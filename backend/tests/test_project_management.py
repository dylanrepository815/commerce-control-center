from sqlalchemy import select

from app.db.models import AgentCredential, Approval, AuditEvent, Project, ResearchRun
from conftest import credential, project, research


def test_owner_can_rename_approved_project_without_changing_approval(context):
    client, factory = context
    created = project(client)
    run = research(client, created)
    candidate = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    selected = client.post(
        f"/api/projects/{created['id']}/select-domain",
        json={
            "candidate_id": candidate["id"],
            "confirmed": True,
            "demo_acknowledged": True,
        },
    ).json()

    response = client.patch(
        f"/api/projects/{created['id']}", json={"name": "  Nieuwe naam  "}
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Nieuwe naam"
    assert response.json()["status"] == "BRAND_PENDING"
    assert response.json()["selected_domain"] == selected["selected_domain"]
    assert response.json()["approved_by"] == selected["approved_by"]
    assert response.json()["approved_at"] == selected["approved_at"]
    assert client.get("/api/projects").json()[0]["name"] == "Nieuwe naam"
    with factory() as db:
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "project.renamed")
        )
        assert event.details == {"from": "Test shop", "to": "Nieuwe naam"}
        assert event.actor_type == "OWNER"


def test_rename_rejects_blank_name_and_agent(context):
    client, factory = context
    created = project(client)
    headers = credential(factory, created["id"])
    assert (
        client.patch(f"/api/projects/{created['id']}", json={"name": "   "}).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/projects/{created['id']}",
            json={"name": "Agent rename"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.get(f"/api/projects/{created['id']}").json()["name"] == "Test shop"


def test_delete_hides_project_and_keeps_audit_history(context):
    client, factory = context
    created = project(client)
    response = client.request(
        "DELETE",
        f"/api/projects/{created['id']}",
        json={"confirm_name": created["name"]},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": True, "project_id": created["id"]}
    assert client.get("/api/projects").json() == []
    assert client.get(f"/api/projects/{created['id']}").status_code == 404
    assert (
        client.request(
            "DELETE",
            f"/api/projects/{created['id']}",
            json={"confirm_name": created["name"]},
        ).status_code
        == 404
    )
    with factory() as db:
        saved = db.get(Project, created["id"])
        assert saved and saved.deleted_at
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "project.deleted")
        )
        assert event and event.project_id == created["id"]
        assert event.details == {"name": created["name"]}
    assert client.get(f"/api/activity?project_id={created['id']}").json()


def test_delete_needs_exact_confirmation_and_owner(context):
    client, factory = context
    created = project(client)
    headers = credential(factory, created["id"])
    endpoint = f"/api/projects/{created['id']}"
    assert (
        client.request(
            "DELETE", endpoint, json={"confirm_name": "Wrong name"}
        ).status_code
        == 422
    )
    assert (
        client.request(
            "DELETE", endpoint, json={"confirm_name": created["name"]}, headers=headers
        ).status_code
        == 403
    )
    assert client.get(endpoint).status_code == 200


def test_delete_closes_pending_approval_and_revokes_agent(context):
    client, factory = context
    created = project(client)
    run = research(client, created)
    headers = credential(factory, created["id"])
    assert (
        client.request(
            "DELETE",
            f"/api/projects/{created['id']}",
            json={"confirm_name": created["name"]},
        ).status_code
        == 200
    )
    assert client.get("/api/approvals").json() == []
    assert (
        client.get(f"/api/candidates/{run['candidates'][0]['id']}/report").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/agent/projects/{created['id']}/input", headers=headers
        ).status_code
        == 401
    )
    with factory() as db:
        assert db.scalar(select(Approval)).state == "REJECTED"
        assert db.scalar(select(AgentCredential)).revoked


def test_delete_stops_running_research(context):
    client, factory = context
    created = project(client)
    headers = credential(factory, created["id"])
    run = client.post(f"/api/agent/projects/{created['id']}/runs", headers=headers)
    assert run.status_code == 201, run.text
    assert (
        client.request(
            "DELETE",
            f"/api/projects/{created['id']}",
            json={"confirm_name": created["name"]},
        ).status_code
        == 200
    )
    with factory() as db:
        assert db.get(ResearchRun, run.json()["id"]).state == "FAILED"


def test_delete_approved_project_preserves_decision(context):
    client, factory = context
    created = project(client)
    run = research(client, created)
    candidate = next(c for c in run["candidates"] if c["final_status"] == "PASS")
    approved = client.post(
        f"/api/projects/{created['id']}/select-domain",
        json={
            "candidate_id": candidate["id"],
            "confirmed": True,
            "demo_acknowledged": True,
        },
    )
    assert approved.status_code == 200
    deleted = client.request(
        "DELETE",
        f"/api/projects/{created['id']}",
        json={"confirm_name": created["name"]},
    )
    assert deleted.status_code == 200, deleted.text
    with factory() as db:
        saved = db.get(Project, created["id"])
        assert saved.deleted_at and saved.status == "BRAND_PENDING"
        assert saved.selected_domain == candidate["domain"]
        assert db.scalar(select(Approval)).state == "APPROVED"
        actions = {
            event.action
            for event in db.scalars(
                select(AuditEvent).where(AuditEvent.project_id == created["id"])
            )
        }
        assert {"approval.granted", "project.deleted"} <= actions
