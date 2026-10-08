from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from app.core.security import owner
from app.db.session import get_db
from app.db.models import Project
from app.audit.service import audit

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=150)
    market: str = Field(min_length=1, max_length=100)
    niche: str = Field(min_length=1, max_length=200)


def get_project(db, id, lock=False):
    query = select(Project).where(Project.id == id)
    if lock:
        query = query.with_for_update()
    project = db.scalar(query)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("")
def projects(actor=Depends(owner), db=Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()


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
