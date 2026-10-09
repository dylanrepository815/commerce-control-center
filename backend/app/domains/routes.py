from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from app.core.security import owner, principal, agent_for
from app.core.config import settings
from app.db.session import get_db
from app.db.models import ResearchRun, Candidate, Evidence, Approval, now
from app.projects.routes import get_project
from app.domains.schemas import ResearchSubmission
from app.domains.providers.fixture import FixtureProvider
from app.domains.service import start_run, complete_run
from app.audit.service import audit

router = APIRouter(tags=["domain research"])


@router.post("/projects/{project_id}/research/fixture", status_code=201)
def fixture(
    project_id: str, request: Request, actor=Depends(owner), db=Depends(get_db)
):
    if not settings().enable_fixtures:
        raise HTTPException(403, "Development fixtures are disabled")
    project = get_project(db, project_id, lock=True)
    provider = FixtureProvider()
    run = start_run(db, project, actor, provider.key, True, request.state.request_id)
    db.commit()
    try:
        submission = ResearchSubmission(
            candidates=provider.research(project.id, project.market, project.niche)
        )
        project = get_project(db, project_id, lock=True)
        run = db.scalar(
            select(ResearchRun).where(ResearchRun.id == run.id).with_for_update()
        )
        complete_run(db, project, run, submission, actor, request.state.request_id)
        db.commit()
    except Exception:
        db.rollback()
        run = db.get(ResearchRun, run.id)
        run.state = "FAILED"
        run.failure = "Provider failed; see correlated server error."
        run.completed_at = now()
        audit(
            db,
            actor,
            "agent.run_failed",
            project_id,
            run.id,
            {"provider": provider.key},
            outcome="FAILURE",
            request_id=request.state.request_id,
        )
        db.commit()
        raise
    return run


@router.get("/projects/{project_id}/research")
def research(project_id: str, actor=Depends(owner), db=Depends(get_db)):
    get_project(db, project_id)
    runs = db.scalars(
        select(ResearchRun)
        .where(ResearchRun.project_id == project_id)
        .order_by(ResearchRun.created_at.desc())
    ).all()
    return [
        {
            **{c.name: getattr(run, c.name) for c in ResearchRun.__table__.columns},
            "candidates": db.scalars(
                select(Candidate)
                .where(Candidate.run_id == run.id)
                .order_by(Candidate.domain_score.desc())
            ).all(),
        }
        for run in runs
    ]


@router.get("/candidates/{candidate_id}/report")
def report(candidate_id: str, actor=Depends(owner), db=Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    run = db.get(ResearchRun, candidate.run_id)
    get_project(db, run.project_id)
    return {
        "candidate": candidate,
        "is_demo": run.is_demo,
        "rule_version": run.rule_version,
        "evidence": db.scalars(
            select(Evidence).where(Evidence.candidate_id == candidate.id)
        ).all(),
    }


@router.get("/agent/projects/{project_id}/input")
def agent_input(project_id: str, actor=Depends(principal), db=Depends(get_db)):
    agent_for(actor, project_id, "research:read")
    project = get_project(db, project_id)
    return {"project_id": project.id, "market": project.market, "niche": project.niche}


@router.post("/agent/projects/{project_id}/runs", status_code=201)
def begin(
    project_id: str, request: Request, actor=Depends(principal), db=Depends(get_db)
):
    agent_for(actor, project_id, "research:submit")
    project = get_project(db, project_id, lock=True)
    run = start_run(
        db, project, actor, "agent-submission", False, request.state.request_id
    )
    db.commit()
    return run


@router.post("/agent/projects/{project_id}/runs/{run_id}/results")
def submit(
    project_id: str,
    run_id: str,
    body: ResearchSubmission,
    request: Request,
    actor=Depends(principal),
    db=Depends(get_db),
):
    agent_for(actor, project_id, "research:submit")
    project = get_project(db, project_id, lock=True)
    run = db.scalar(
        select(ResearchRun).where(ResearchRun.id == run_id).with_for_update()
    )
    if not run or run.project_id != project.id or run.agent_id != actor.id:
        raise HTTPException(404, "Assigned run not found")
    complete_run(db, project, run, body, actor, request.state.request_id)
    db.commit()
    return run


@router.post("/projects/{project_id}/research/retry")
def retry_research(
    project_id: str, request: Request, actor=Depends(owner), db=Depends(get_db)
):
    project = get_project(db, project_id, lock=True)
    if project.status == "BRAND_PENDING":
        raise HTTPException(409, "An approved project cannot restart research in V1")
    running = db.scalars(
        select(ResearchRun)
        .where(ResearchRun.project_id == project_id, ResearchRun.state == "RUNNING")
        .with_for_update()
    ).all()
    for run in running:
        run.state = "FAILED"
        run.completed_at = now()
        run.failure = "Stopped by Owner to restart research"
        audit(
            db,
            actor,
            "agent.run_failed",
            project_id,
            run.id,
            {"reason": "owner_restart"},
            outcome="FAILURE",
            request_id=request.state.request_id,
        )
    pending = db.scalars(
        select(Approval)
        .where(Approval.project_id == project_id, Approval.state == "PENDING")
        .with_for_update()
    ).all()
    for approval in pending:
        approval.state = "REJECTED"
        approval.decided_by = actor.id
        approval.decided_at = now()
        approval.note = "Superseded by Owner research restart"
        audit(
            db,
            actor,
            "approval.superseded",
            project_id,
            approval.id,
            request_id=request.state.request_id,
        )
    old = project.status
    project.status = "DOMAIN_RESEARCH"
    audit(
        db,
        actor,
        "research.restarted",
        project_id,
        project_id,
        request_id=request.state.request_id,
    )
    if old != project.status:
        audit(
            db,
            actor,
            "project.status_changed",
            project_id,
            project_id,
            {"from": old, "to": project.status},
            request_id=request.state.request_id,
        )
    db.commit()
    return project
