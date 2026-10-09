from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


J = JSON().with_variant(JSONB, "postgresql")


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="OWNER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("role = 'OWNER'"),)


class Session(Identity, Base):
    __tablename__ = "sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Agent(Identity, Base):
    __tablename__ = "agents"
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    capabilities: Mapped[list] = mapped_column(J, default=list)


class AgentCredential(Identity, Base):
    __tablename__ = "agent_credentials"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Project(Identity, Base):
    __tablename__ = "projects"
    name: Mapped[str] = mapped_column(String(150))
    market: Mapped[str] = mapped_column(String(100))
    niche: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="DOMAIN_RESEARCH")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    selected_domain: Mapped[str | None] = mapped_column(String(253))
    selected_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("domain_candidates.id", use_alter=True, name="fk_selected_candidate")
    )
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=now, onupdate=now
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('DOMAIN_RESEARCH','DOMAIN_SELECTION','BRAND_PENDING')"
        ),
    )


class ResearchRun(Identity, Base):
    __tablename__ = "research_runs"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"))
    state: Mapped[str] = mapped_column(String(20), default="RUNNING")
    provider: Mapped[str] = mapped_column(String(100))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    inputs: Mapped[dict] = mapped_column(J)
    rule_version: Mapped[str] = mapped_column(String(30), default="v1")
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failure: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("state IN ('RUNNING','COMPLETED','FAILED')"),)


class Candidate(Identity, Base):
    __tablename__ = "domain_candidates"
    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), index=True)
    domain: Mapped[str] = mapped_column(String(253))
    source: Mapped[str] = mapped_column(String(200))
    acquisition_url: Mapped[str | None] = mapped_column(Text)
    acquisition_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    scamadviser_score: Mapped[int | None] = mapped_column(Integer)
    history_status: Mapped[str] = mapped_column(String(20))
    backlink_status: Mapped[str] = mapped_column(String(20))
    safety_status: Mapped[str] = mapped_column(String(20))
    niche_fit_score: Mapped[int | None] = mapped_column(Integer)
    domain_score: Mapped[int] = mapped_column(Integer)
    historical_categories: Mapped[list] = mapped_column(J, default=list)
    warnings: Mapped[list] = mapped_column(J, default=list)
    rejection_reasons: Mapped[list] = mapped_column(J, default=list)
    final_status: Mapped[str] = mapped_column(String(10))
    research_timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    __table_args__ = (
        UniqueConstraint("run_id", "domain"),
        CheckConstraint("scamadviser_score BETWEEN 0 AND 100"),
        CheckConstraint("niche_fit_score BETWEEN 0 AND 100"),
        CheckConstraint("domain_score BETWEEN 0 AND 100"),
        CheckConstraint("final_status IN ('PASS','FAIL','REVIEW')"),
        CheckConstraint("acquisition_price >= 0"),
    )


class Evidence(Identity, Base):
    __tablename__ = "research_evidence"
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("domain_candidates.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(100))
    check_type: Mapped[str] = mapped_column(String(30))
    source_reference: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    findings: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    categories: Mapped[list] = mapped_column(J, default=list)


class Approval(Identity, Base):
    __tablename__ = "approvals"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), unique=True)
    type: Mapped[str] = mapped_column(String(30), default="DOMAIN_SELECTION")
    state: Mapped[str] = mapped_column(String(20), default="PENDING")
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("domain_candidates.id"))
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("state IN ('PENDING','APPROVED','REJECTED')"),)


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100))
    actor_type: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100), index=True)
    target: Mapped[str | None] = mapped_column(String(100))
    request_id: Mapped[str] = mapped_column(String(36))
    outcome: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    details: Mapped[dict] = mapped_column(J, default=dict)
