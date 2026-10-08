"""Runs against disposable PostgreSQL databases when TEST_POSTGRES_URL is set."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import text, select
from sqlalchemy.exc import DBAPIError
from conftest import project, research, credential
from app.db.models import Candidate, AuditEvent, ResearchRun
from app.domains.providers.fixture import FixtureProvider
from app.domains.evaluation import evaluate

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="PostgreSQL integration runtime unavailable",
)


def test_postgres_audit_is_append_only(context):
    client, factory = context
    project(client)
    for statement in [
        "UPDATE audit_events SET action='tampered'",
        "DELETE FROM audit_events",
        "TRUNCATE audit_events",
    ]:
        with factory() as db, pytest.raises(DBAPIError):
            db.execute(text(statement))
            db.commit()


def test_postgres_completed_results_and_provenance_are_immutable(context):
    client, factory = context
    p = project(client)
    research(client, p)
    for statement in [
        "UPDATE domain_candidates SET domain_score=100",
        "DELETE FROM domain_candidates",
        "UPDATE research_evidence SET findings='changed'",
        "UPDATE research_runs SET is_demo=false",
    ]:
        with factory() as db, pytest.raises(DBAPIError):
            db.execute(text(statement))
            db.commit()


def test_postgres_twenty_first_candidate_rejected(context):
    client, factory = context
    p = project(client)
    headers = credential(factory, p["id"])
    run = client.post(f"/api/agent/projects/{p['id']}/runs", headers=headers).json()
    raw = FixtureProvider().research("test", "NL", "retail")[0]
    data = raw.model_dump(exclude={"evidence", "warnings"}, mode="json")
    with factory() as db:
        for i in range(20):
            candidate = Candidate(
                run_id=run["id"],
                **{**data, "domain": f"candidate-{i}.example"},
                **evaluate(raw),
            )
            db.add(candidate)
            db.flush()
        db.commit()
    with factory() as db, pytest.raises(DBAPIError):
        db.add(
            Candidate(
                run_id=run["id"],
                **{**data, "domain": "candidate-21.example"},
                **evaluate(raw),
            )
        )
        db.commit()


def test_postgres_concurrent_approval_has_one_winner(context):
    from fastapi.testclient import TestClient
    from app.main import app

    client, factory = context
    p = project(client)
    run = research(client, p)
    candidate = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    barrier = Barrier(2)

    def approve():
        with TestClient(app) as other:
            other.cookies.update(client.cookies)
            other.headers.update(client.headers)
            barrier.wait()
            return other.post(
                f"/api/projects/{p['id']}/select-domain",
                json={
                    "candidate_id": candidate["id"],
                    "confirmed": True,
                    "demo_acknowledged": True,
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: approve(), range(2)))
    assert sorted(statuses) == [200, 409]
    with factory() as db:
        assert (
            len(
                db.scalars(
                    select(AuditEvent).where(AuditEvent.action == "approval.granted")
                ).all()
            )
            == 1
        )
