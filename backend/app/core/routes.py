import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.config import settings
from app.core.security import Actor, owner, check_origin, digest, passwords, DUMMY_HASH
from app.db.session import get_db
from app.db.models import User, Session, now
from app.audit.service import audit

router = APIRouter(prefix="/auth", tags=["authentication"])


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@router.post("/login")
def login(body: Login, request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not valid or not user or not user.active:
        raise HTTPException(401, "Invalid email or password")
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.add(
        Session(
            user_id=user.id,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            expires_at=now() + timedelta(hours=settings().session_hours),
        )
    )
    audit(
        db, Actor(user.id, "OWNER"), "owner.login", request_id=request.state.request_id
    )
    db.commit()
    for name, value, httponly in [
        ("cc_session", token, True),
        ("cc_csrf", csrf, False),
    ]:
        response.set_cookie(
            name,
            value,
            httponly=httponly,
            secure=settings().cookie_secure,
            samesite="strict",
            max_age=settings().session_hours * 3600,
            path="/",
        )
    return {"email": user.email, "role": "OWNER"}


@router.get("/me")
def me(actor=Depends(owner)):
    return {"id": actor.id, "email": actor.email, "role": actor.kind}


@router.post("/logout")
def logout(
    request: Request, response: Response, actor=Depends(owner), db=Depends(get_db)
):
    session = db.scalar(
        select(Session).where(
            Session.token_hash == digest(request.cookies.get("cc_session", ""))
        )
    )
    if session:
        db.delete(session)
    audit(db, actor, "owner.logout", request_id=request.state.request_id)
    db.commit()
    response.delete_cookie("cc_session", path="/")
    response.delete_cookie("cc_csrf", path="/")
    return {"ok": True}
