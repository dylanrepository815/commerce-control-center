import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["ENABLE_FIXTURES"] = "true"
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db.session import Base, get_db
from app.db.models import User, Agent, AgentCredential, now
from app.core.security import passwords, digest
from app.core.config import settings
from datetime import timedelta
import app.main as main


@pytest.fixture
def context(monkeypatch):
    settings.cache_clear()
    admin = None
    if os.environ.get("TEST_POSTGRES_URL"):
        from alembic.config import Config
        from alembic import command

        base = make_url(os.environ["TEST_POSTGRES_URL"])
        admin = create_engine(
            base.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        database = "cc_test_" + uuid4().hex
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
        migration_url = base.set(database=database).render_as_string(
            hide_password=False
        )
        monkeypatch.setenv("MIGRATION_DATABASE_URL", migration_url)
        command.upgrade(Config("alembic.ini"), "head")
        runtime_url = base.set(
            database=database,
            username="cc_app",
            password=os.environ["TEST_RUNTIME_PASSWORD"],
        )
        engine = create_engine(runtime_url, pool_pre_ping=True)
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def fk(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override():
        with factory() as db:
            yield db

    main.app.dependency_overrides[get_db] = override
    monkeypatch.setattr(main, "SessionLocal", factory)
    with factory() as db:
        user = User(
            email="owner@test.example",
            password_hash=passwords.hash("test-password-12345"),
        )
        db.add(user)
        db.commit()
    with TestClient(main.app) as client:
        client.headers["Origin"] = os.environ.get(
            "TEST_APP_ORIGIN", "http://localhost:3000"
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "owner@test.example", "password": "test-password-12345"},
        )
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = client.cookies.get("cc_csrf")
        yield client, factory
    main.app.dependency_overrides.clear()
    engine.dispose()
    if admin:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()


def project(client):
    response = client.post(
        "/api/projects",
        json={"name": "Test shop", "market": "Netherlands", "niche": "Home goods"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def research(client, p):
    response = client.post(f"/api/projects/{p['id']}/research/fixture")
    assert response.status_code == 201, response.text
    return client.get(f"/api/projects/{p['id']}/research").json()[0]


def credential(factory, project_id):
    with factory() as db:
        agent = Agent(
            key="test-agent",
            name="Test Agent",
            enabled=True,
            capabilities=["research:read", "research:submit"],
        )
        db.add(agent)
        db.flush()
        db.add(
            AgentCredential(
                agent_id=agent.id,
                project_id=project_id,
                token_hash=digest("agent-secret"),
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    return {"Authorization": "Bearer agent-secret"}
