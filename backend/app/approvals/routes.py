from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from app.core.security import owner
from app.db.models import Approval, Candidate, ResearchRun, Project, now
from app.db.session import get_db
from app.projects.routes import get_project
from app.audit.service import audit

router = APIRouter(tags=["approvals"])


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str = Field(min_length=36, max_length=36)
    confirmed: bool
    demo_acknowledged: bool = False


@router.get("/approvals")
def approvals(actor=Depends(owner), db=Depends(get_db)):
    return db.scalars(
        select(Approval)
        .join(Project, Approval.project_id == Project.id)
        .where(Project.deleted_at.is_(None))
        .order_by(Approval.created_at.desc())
    ).all()


@router.post("/projects/{project_id}/select-domain")
def select_domain(
    project_id: str,
    body: Selection,
    request: Request,
    actor=Depends(owner),
    db=Depends(get_db),
):
    project = get_project(db, project_id, lock=True)
    if project.status != "DOMAIN_SELECTION":
        raise HTTPException(409, "Project is not awaiting domain selection")
    candidate = db.get(Candidate, body.candidate_id)
    run = db.get(ResearchRun, candidate.run_id) if candidate else None
    if not candidate or not run or run.project_id != project.id:
        raise HTTPException(404, "Candidate does not belong to this project")
    approval = db.scalar(
        select(Approval)
        .where(
            Approval.project_id == project.id,
            Approval.run_id == run.id,
            Approval.state == "PENDING",
        )
        .with_for_update()
    )
    if not approval or run.state != "COMPLETED":
        raise HTTPException(409, "Research approval is no longer pending")
    if candidate.final_status != "PASS":
        raise HTTPException(422, "Only PASS candidates can be selected")
    if not body.confirmed:
        raise HTTPException(422, "Explicit Owner confirmation required")
    if run.is_demo and not body.demo_acknowledged:
        raise HTTPException(422, "Acknowledge that this is synthetic demo research")
    timestamp = now()
    project.selected_domain = candidate.domain
    project.selected_candidate_id = candidate.id
    project.approved_by = actor.id
    project.approved_at = timestamp
    project.status = "BRAND_PENDING"
    approval.state = "APPROVED"
    approval.candidate_id = candidate.id
    approval.decided_by = actor.id
    approval.decided_at = timestamp
    context = {
        "domain": candidate.domain,
        "candidate_id": candidate.id,
        "is_demo": run.is_demo,
    }
    for action in ["approval.granted", "domain.selected"]:
        audit(
            db,
            actor,
            action,
            project.id,
            approval.id,
            context,
            request_id=request.state.request_id,
        )
    audit(
        db,
        actor,
        "project.status_changed",
        project.id,
        project.id,
        {"from": "DOMAIN_SELECTION", "to": "BRAND_PENDING"},
        request_id=request.state.request_id,
    )
    db.commit()
    return project
