import logging
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from app.db.session import SessionLocal, get_db
from app.core.security import Actor
from app.audit.service import audit
from app.core import routes as auth
from app.projects import routes as projects
from app.domains import routes as domains
from app.approvals import routes as approvals
from app.audit import routes as activity
from app.agents import routes as agents

app = FastAPI(
    title="Commerce Control Center",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
log = logging.getLogger("control_center")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Request failed: %s", request.state.request_id)
        response = JSONResponse(
            {"detail": "Internal error", "request_id": request.state.request_id},
            status_code=500,
        )
    if response.status_code >= 400:
        actor = getattr(request.state, "actor", Actor("anonymous", "ANONYMOUS"))
        try:
            with SessionLocal() as db:
                audit(
                    db,
                    actor,
                    "request.denied" if response.status_code < 500 else "request.error",
                    details={
                        "method": request.method,
                        "path": request.url.path[:250],
                        "status": response.status_code,
                    },
                    outcome="FAILURE",
                    request_id=request.state.request_id,
                )
                db.commit()
        except Exception:
            log.exception("Audit persistence failed: %s", request.state.request_id)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Never echo rejected passwords or authentication payloads.
    return JSONResponse(
        {
            "detail": [
                {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ]
        },
        status_code=422,
    )


@app.get("/health")
def health(db=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "Database unavailable")
    return {"status": "ok", "database": "ok"}


for router in [
    auth.router,
    projects.router,
    domains.router,
    approvals.router,
    activity.router,
    agents.router,
]:
    app.include_router(router, prefix="/api")
