from fastapi import HTTPException
from sqlalchemy import select
from app.db.models import ResearchRun, Candidate, Evidence, Approval, now
from app.domains.schemas import ResearchSubmission
from app.domains.evaluation import evaluate, RULE_VERSION
from app.audit.service import audit


def start_run(db, project, actor, provider, is_demo, request_id):
    if project.status != "DOMAIN_RESEARCH":
        raise HTTPException(409, "Research can only start during DOMAIN_RESEARCH")
    running = db.scalar(
        select(ResearchRun).where(
            ResearchRun.project_id == project.id, ResearchRun.state == "RUNNING"
        )
    )
    if running:
        raise HTTPException(409, "Research is already running")
    run = ResearchRun(
        project_id=project.id,
        agent_id=actor.id if actor.kind == "AGENT" else None,
        provider=provider,
        is_demo=is_demo,
        inputs={
            "project_id": project.id,
            "market": project.market,
            "niche": project.niche,
        },
        rule_version=RULE_VERSION,
    )
    db.add(run)
    db.flush()
    audit(
        db,
        actor,
        "agent.run_started",
        project.id,
        run.id,
        {"provider": provider, "is_demo": is_demo},
        request_id=request_id,
    )
    return run


def complete_run(db, project, run, submission: ResearchSubmission, actor, request_id):
    if run.state != "RUNNING" or project.status != "DOMAIN_RESEARCH":
        raise HTTPException(409, "Research is not open")
    # Revalidate at the persistence boundary, including the 20-candidate limit.
    submission = ResearchSubmission.model_validate(submission.model_dump())
    eligible = 0
    for item in submission.candidates:
        data = item.model_dump(exclude={"evidence", "warnings"}, mode="json")
        candidate = Candidate(run_id=run.id, **data, **evaluate(item))
        db.add(candidate)
        db.flush()
        for evidence in item.evidence:
            db.add(Evidence(candidate_id=candidate.id, **evidence.model_dump()))
        eligible += candidate.final_status in ("PASS", "REVIEW")
        audit(
            db,
            actor,
            "domain.result_recorded",
            project.id,
            candidate.id,
            {
                "domain": candidate.domain,
                "status": candidate.final_status,
                "is_demo": run.is_demo,
                "rejection_reasons": candidate.rejection_reasons,
            },
            request_id=request_id,
        )
    db.flush()  # Persist evidence before the completed-run immutability guard applies.
    run.state = "COMPLETED"
    run.completed_at = now()
    if eligible:
        project.status = "DOMAIN_SELECTION"
        db.add(Approval(project_id=project.id, run_id=run.id))
        audit(
            db,
            actor,
            "project.status_changed",
            project.id,
            project.id,
            {"from": "DOMAIN_RESEARCH", "to": "DOMAIN_SELECTION"},
            request_id=request_id,
        )
    audit(
        db,
        actor,
        "agent.run_completed",
        project.id,
        run.id,
        {"candidate_count": len(submission.candidates), "is_demo": run.is_demo},
        request_id=request_id,
    )
