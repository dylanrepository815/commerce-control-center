from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.core.security import owner
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Agent

router = APIRouter(tags=["configuration"])


@router.get("/agents")
def agents(actor=Depends(owner), db=Depends(get_db)):
    return db.scalars(select(Agent).order_by(Agent.name)).all()


@router.get("/settings")
def configuration(actor=Depends(owner)):
    return {
        "fixtures_enabled": settings().enable_fixtures,
        "live_providers_configured": False,
        "rule_version": "v1",
        "scamadviser_minimum": 75,
        "candidate_limit": 20,
        "approval_policy": "OWNER_ONLY_PASS_ONLY",
        "purchasing_enabled": False,
        "storage_backend": "sqlite-preview"
        if settings().database_url.startswith("sqlite")
        else "postgresql",
        "cookie_secure": settings().cookie_secure,
    }
