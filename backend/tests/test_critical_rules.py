import pytest
from pydantic import ValidationError
from sqlalchemy import select, func
from app.domains.schemas import ResearchSubmission
from app.domains.providers.fixture import FixtureProvider
from app.domains.evaluation import evaluate, FORBIDDEN
from app.db.models import AuditEvent, Approval, Project, Candidate, ResearchRun
from app.main import app
from conftest import project, research, credential


def pass_input():
    return FixtureProvider().research("test", "NL", "retail")[0]


def choose(client, p, c, **extra):
    return client.post(
        f"/api/projects/{p['id']}/select-domain",
        json={
            "candidate_id": c["id"],
            "confirmed": True,
            "demo_acknowledged": True,
            **extra,
        },
    )


@pytest.mark.parametrize("score", [0, 50, 74])
def test_scamadviser_below_75_fails(score):
    c = pass_input()
    c.scamadviser_score = score
    assert evaluate(c)["final_status"] == "FAIL"


def test_scamadviser_threshold_and_alone_is_insufficient():
    c = pass_input()
    c.scamadviser_score = 75
    assert evaluate(c)["final_status"] == "PASS"
    c.evidence = [e for e in c.evidence if e.check_type == "scamadviser"]
    assert evaluate(c)["final_status"] == "REVIEW"


@pytest.mark.parametrize(
    "category",
    sorted(FORBIDDEN) + ["GAMBLING / CASINO", "Adult / Pornography", "severe_spam"],
)
def test_verified_forbidden_history_fails(category):
    c = pass_input()
    c.evidence[0].categories = [category]
    assert evaluate(c)["final_status"] == "FAIL"


def test_unverified_history_and_missing_score_require_review():
    c = pass_input()
    c.evidence[0].categories = ["casino"]
    c.evidence[0].verified = False
    assert evaluate(c)["final_status"] == "REVIEW"
    c = pass_input()
    c.scamadviser_score = None
    assert evaluate(c)["final_status"] == "REVIEW"


@pytest.mark.parametrize("status", ["REVIEW", "FAIL"])
def test_nonpass_cannot_be_selected(context, status):
    client, factory = context
    p = project(client)
    run = research(client, p)
    c = next(c for c in run["candidates"] if c["final_status"] == status)
    assert choose(client, p, c).status_code == 422
    assert client.get(f"/api/projects/{p['id']}").json()["status"] == "DOMAIN_SELECTION"
    with factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "approval.granted")
            )
            == 0
        )
        assert db.scalar(select(Approval)).state == "PENDING"


def test_agent_cannot_select_or_approve(context):
    client, factory = context
    p = project(client)
    run = research(client, p)
    c = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    headers = credential(factory, p["id"])
    for endpoint in [f"/api/projects/{p['id']}/select-domain", "/api/approvals"]:
        response = client.request(
            "POST" if "select-domain" in endpoint else "GET",
            endpoint,
            headers=headers,
            json={
                "candidate_id": c["id"],
                "confirmed": True,
                "demo_acknowledged": True,
            },
        )
        assert response.status_code == 403
    with factory() as db:
        assert db.scalar(select(Approval)).state == "PENDING"
        assert db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "request.denied", AuditEvent.actor_type == "AGENT"
            )
        )


def test_candidate_must_belong_to_project(context):
    client, _ = context
    p = project(client)
    run = research(client, p)
    other = project(client)
    research(client, other)
    c = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    assert choose(client, other, c).status_code == 404


def test_owner_approval_transition_and_atomic_audit(context):
    client, factory = context
    p = project(client)
    run = research(client, p)
    c = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    assert client.get(f"/api/projects/{p['id']}").json()["status"] == "DOMAIN_SELECTION"
    response = choose(client, p, c)
    assert response.status_code == 200, response.text
    selected = response.json()
    assert selected["status"] == "BRAND_PENDING"
    assert selected["selected_domain"] == c["domain"]
    assert selected["approved_at"] and selected["approved_by"]
    with factory() as db:
        approval = db.scalar(select(Approval))
        assert approval.state == "APPROVED"
        assert approval.decided_by == selected["approved_by"]
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action.in_(["approval.granted", "domain.selected"])
            )
        ).all()
        assert len(events) == 2
        assert {e.request_id for e in events} == {response.headers["x-request-id"]}
        assert all(e.actor_type == "OWNER" and e.details["is_demo"] for e in events)
    assert choose(client, p, c).status_code == 409


def test_confirmation_and_fixture_acknowledgment_required(context):
    client, _ = context
    p = project(client)
    run = research(client, p)
    c = run["candidates"][0]
    assert choose(client, p, c, confirmed=False).status_code == 422
    assert choose(client, p, c, demo_acknowledged=False).status_code == 422


def test_no_payment_or_purchase_endpoints():
    schema = app.openapi()
    expected = {
        "/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/projects",
        "/api/projects/{project_id}",
        "/api/projects/{project_id}/research/fixture",
        "/api/projects/{project_id}/research/retry",
        "/api/projects/{project_id}/research",
        "/api/candidates/{candidate_id}/report",
        "/api/agent/projects/{project_id}/input",
        "/api/agent/projects/{project_id}/runs",
        "/api/agent/projects/{project_id}/runs/{run_id}/results",
        "/api/approvals",
        "/api/projects/{project_id}/select-domain",
        "/api/activity",
        "/api/agents",
        "/api/settings",
    }
    assert set(schema["paths"]) == expected
    assert not any(
        term in path.lower()
        for path in schema["paths"]
        for term in ["payment", "purchase", "checkout", "advertising"]
    )


def test_limit_20_and_duplicate_validation():
    values = [
        pass_input().model_copy(update={"domain": f"domain-{i}.example"})
        for i in range(21)
    ]
    assert len(ResearchSubmission(candidates=values[:20]).candidates) == 20
    with pytest.raises(ValidationError):
        ResearchSubmission(candidates=values)
    with pytest.raises(ValidationError):
        ResearchSubmission(candidates=[values[0], values[0]])


def test_agent_submission_enforces_limit_and_computes_status(context):
    client, factory = context
    p = project(client)
    headers = credential(factory, p["id"])
    response = client.post(f"/api/agent/projects/{p['id']}/runs", headers=headers)
    assert response.status_code == 201, response.text
    run = response.json()
    endpoint = f"/api/agent/projects/{p['id']}/runs/{run['id']}/results"
    values = [
        pass_input()
        .model_copy(update={"domain": f"domain-{i}.example"})
        .model_dump(mode="json")
        for i in range(21)
    ]
    assert (
        client.post(endpoint, headers=headers, json={"candidates": values}).status_code
        == 422
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Candidate)) == 0
    response = client.post(endpoint, headers=headers, json={"candidates": values[:20]})
    assert response.status_code == 200, response.text
    assert (
        len(client.get(f"/api/projects/{p['id']}/research").json()[0]["candidates"])
        == 20
    )
    assert (
        client.post(
            endpoint, headers=headers, json={"candidates": values[:1]}
        ).status_code
        == 409
    )


def test_agent_scope_and_no_project_or_settings_mutation(context):
    client, factory = context
    p = project(client)
    other = project(client)
    headers = credential(factory, p["id"])
    assert (
        client.get(f"/api/agent/projects/{p['id']}/input", headers=headers).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/agent/projects/{other['id']}/input", headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Unauthorized", "market": "NL", "niche": "x"},
        ).status_code
        == 403
    )
    assert client.get("/api/settings", headers=headers).status_code == 403


def test_csrf_and_invalid_origin_block_writes(context):
    client, _ = context
    body = {"name": "test", "market": "NL", "niche": "x"}
    assert (
        client.post(
            "/api/projects", json=body, headers={"X-CSRF-Token": ""}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/projects", json=body, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_unauthenticated_and_logout(context):
    client, _ = context
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/projects").status_code == 401


def test_fixtures_can_be_disabled(context, monkeypatch):
    from app.core.config import settings

    client, _ = context
    p = project(client)
    monkeypatch.setenv("ENABLE_FIXTURES", "false")
    settings.cache_clear()
    assert client.post(f"/api/projects/{p['id']}/research/fixture").status_code == 403


def test_audit_failure_rolls_back_approval(context, monkeypatch):
    import app.approvals.routes as routes

    client, factory = context
    p = project(client)
    run = research(client, p)

    def broken(*a, **k):
        raise RuntimeError("Simulated audit failure")

    monkeypatch.setattr(routes, "audit", broken)
    assert choose(client, p, run["candidates"][0]).status_code == 500
    with factory() as db:
        assert db.get(Project, p["id"]).status == "DOMAIN_SELECTION"
        assert db.scalar(select(Approval)).state == "PENDING"


def test_provider_failure_is_logged(context, monkeypatch):
    client, factory = context
    p = project(client)

    def broken(*a, **k):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(FixtureProvider, "research", broken)
    assert client.post(f"/api/projects/{p['id']}/research/fixture").status_code == 500
    with factory() as db:
        assert db.scalar(select(ResearchRun)).state == "FAILED"
        assert db.scalar(
            select(AuditEvent).where(AuditEvent.action == "agent.run_failed")
        )
        assert db.get(Project, p["id"]).status == "DOMAIN_RESEARCH"


def test_restart_supersedes_stale_approval_and_preserves_history(context):
    client, factory = context
    p = project(client)
    run = research(client, p)
    old = run["candidates"][0]
    assert client.post(f"/api/projects/{p['id']}/research/retry").status_code == 200
    research(client, p)
    assert len(client.get(f"/api/projects/{p['id']}/research").json()) == 2
    assert choose(client, p, old).status_code == 409
    with factory() as db:
        assert (
            db.scalar(select(Approval).where(Approval.run_id == run["id"])).state
            == "REJECTED"
        )


def test_restart_recovers_interrupted_run_and_agent_cannot_restart(context):
    client, factory = context
    p = project(client)
    headers = credential(factory, p["id"])
    run = client.post(f"/api/agent/projects/{p['id']}/runs", headers=headers).json()
    assert (
        client.post(
            f"/api/projects/{p['id']}/research/retry", headers=headers
        ).status_code
        == 403
    )
    assert client.post(f"/api/projects/{p['id']}/research/retry").status_code == 200
    with factory() as db:
        assert db.get(ResearchRun, run["id"]).state == "FAILED"
