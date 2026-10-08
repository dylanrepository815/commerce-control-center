from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.core.security import owner
from app.db.session import get_db
from app.db.models import AuditEvent

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
def activity(
    project_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    actor=Depends(owner),
    db=Depends(get_db),
):
    query = select(AuditEvent)
    if project_id:
        query = query.where(AuditEvent.project_id == project_id)
    return db.scalars(
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id)
        .offset(offset)
        .limit(limit)
    ).all()
