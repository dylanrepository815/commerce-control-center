from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from app.core.security import owner
from app.db.session import get_db
from app.db.models import Project, Approval, ResearchRun, AgentCredential, now
from app.audit.service import audit

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=150)
    market: str = Field(min_length=1, max_length=100)
    niche: str = Field(min_length=1, max_length=200)


class ProjectRename(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=150)


class ProjectDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_name: str


def get_project(db, id, lock=False):
    query = select(Project).where(Project.id == id, Project.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    project = db.scalar(query)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("")
def projects(actor=Depends(owner), db=Depends(get_db)):
    return db.scalars(
        select(Project)
        .where(Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    ).all()


@router.post("", status_code=201)
def create(
    body: ProjectCreate, request: Request, actor=Depends(owner), db=Depends(get_db)
):
    project = Project(**body.model_dump(), created_by=actor.id)
    db.add(project)
    db.flush()
    audit(
        db,
        actor,
        "project.created",
        project.id,
        project.id,
        {"name": project.name},
        request_id=request.state.request_id,
    )
    audit(
        db,
        actor,
        "project.status_changed",
        project.id,
        project.id,
        {"from": None, "to": "DOMAIN_RESEARCH"},
        request_id=request.state.request_id,
    )
    db.commit()
    return project


@router.get("/{project_id}")
def detail(project_id: str, actor=Depends(owner), db=Depends(get_db)):
    return get_project(db, project_id)


@router.patch("/{project_id}")
def rename(
    project_id: str,
    body: ProjectRename,
    request: Request,
    actor=Depends(owner),
    db=Depends(get_db),
):
    project = get_project(db, project_id, lock=True)
    if project.name != body.name:
        old_name = project.name
        project.name = body.name
        audit(
            db,
            actor,
            "project.renamed",
            project.id,
            project.id,
            {"from": old_name, "to": body.name},
            request_id=request.state.request_id,
        )
        db.commit()
    return project


@router.delete("/{project_id}")
def delete(
    project_id: str,
    body: ProjectDelete,
    request: Request,
    actor=Depends(owner),
    db=Depends(get_db),
):
    project = get_project(db, project_id, lock=True)
    if body.confirm_name != project.name:
        raise HTTPException(422, "Type the exact project name to confirm deletion")
    timestamp = now()
    for run in db.scalars(
        select(ResearchRun)
        .where(ResearchRun.project_id == project.id, ResearchRun.state == "RUNNING")
        .with_for_update()
    ):
        run.state = "FAILED"
        run.failure = "Project deleted by Owner"
        run.completed_at = timestamp
        audit(
            db,
            actor,
            "agent.run_failed",
            project.id,
            run.id,
            {"reason": "project_deleted"},
            outcome="FAILURE",
            request_id=request.state.request_id,
        )
    for approval in db.scalars(
        select(Approval)
        .where(Approval.project_id == project.id, Approval.state == "PENDING")
        .with_for_update()
    ):
        approval.state = "REJECTED"
        approval.decided_by = actor.id
        approval.decided_at = timestamp
        approval.note = "Project deleted by Owner"
        audit(
            db,
            actor,
            "approval.superseded",
            project.id,
            approval.id,
            {"reason": "project_deleted"},
            request_id=request.state.request_id,
        )
    for credential in db.scalars(
        select(AgentCredential).where(AgentCredential.project_id == project.id)
    ):
        credential.revoked = True
    project.deleted_at = timestamp
    audit(
        db,
        actor,
        "project.deleted",
        project.id,
        project.id,
        {"name": project.name},
        request_id=request.state.request_id,
    )
    db.commit()
    return {"deleted": True, "project_id": project.id}
