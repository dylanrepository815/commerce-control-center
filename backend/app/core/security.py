import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from pwdlib import PasswordHash
from app.db.models import Session, User, Agent, AgentCredential
from app.db.session import get_db
from app.core.config import settings

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def future(value):
    return value.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


@dataclass
class Actor:
    id: str
    kind: str
    capabilities: tuple = ()
    project_id: str | None = None
    email: str | None = None


def principal(request: Request, db=Depends(get_db)):
    bearer = request.headers.get("authorization", "")
    if bearer:
        if not bearer.startswith("Bearer "):
            raise HTTPException(401, "Invalid authentication")
        cred = db.scalar(
            select(AgentCredential).where(
                AgentCredential.token_hash == digest(bearer[7:])
            )
        )
        agent = db.get(Agent, cred.agent_id) if cred else None
        if (
            not cred
            or cred.revoked
            or not future(cred.expires_at)
            or not agent
            or not agent.enabled
        ):
            raise HTTPException(401, "Invalid agent credential")
        actor = Actor(agent.id, "AGENT", tuple(agent.capabilities), cred.project_id)
    else:
        token = request.cookies.get("cc_session", "")
        session = (
            db.scalar(select(Session).where(Session.token_hash == digest(token)))
            if token
            else None
        )
        user = db.get(User, session.user_id) if session else None
        if not session or not future(session.expires_at) or not user or not user.active:
            raise HTTPException(401, "Sign in required")
        actor = Actor(user.id, "OWNER", email=user.email)
        request.state.actor = actor
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            check_origin(request)
            csrf = request.headers.get("x-csrf-token", "")
            if not csrf or not secrets.compare_digest(session.csrf_hash, digest(csrf)):
                raise HTTPException(403, "Invalid CSRF token")
    request.state.actor = actor
    return actor


def check_origin(request):
    if request.headers.get("origin") != settings().app_origin:
        raise HTTPException(403, "Untrusted request origin")


def owner(actor=Depends(principal)):
    if actor.kind != "OWNER":
        raise HTTPException(403, "Only the Owner can perform this action")
    return actor


def agent_for(actor, project_id, capability):
    if (
        actor.kind != "AGENT"
        or actor.project_id != project_id
        or capability not in actor.capabilities
    ):
        raise HTTPException(403, "Agent capability or project scope denied")
