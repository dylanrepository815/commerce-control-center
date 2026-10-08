from app.db.models import AuditEvent


def audit(
    db,
    actor,
    action,
    project_id=None,
    target=None,
    details=None,
    outcome="SUCCESS",
    request_id=None,
):
    from uuid import uuid4

    db.add(
        AuditEvent(
            actor_id=actor.id,
            actor_type=actor.kind,
            action=action,
            project_id=project_id,
            target=target,
            details=details or {},
            outcome=outcome,
            request_id=request_id or str(uuid4()),
        )
    )
