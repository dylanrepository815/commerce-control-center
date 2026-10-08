"""Local operator commands. No public setup or credential management endpoint."""

import argparse
import getpass
import secrets
from datetime import timedelta
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models import User, Agent, AgentCredential, Project, now
from app.core.security import Actor, passwords, digest
from app.audit.service import audit


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("create-owner")
    setup.add_argument("--email", required=True)
    agent = sub.add_parser("issue-agent-token")
    agent.add_argument("--project-id", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "create-owner":
            if db.scalar(select(User.id).limit(1)):
                raise SystemExit("Owner already exists; setup is closed.")
            email = args.email.strip().lower()
            if "@" not in email or len(email) > 254:
                raise SystemExit("Enter a valid email address")
            password = getpass.getpass("Owner password (minimum 12 characters): ")
            if len(password) < 12:
                raise SystemExit("Password must contain at least 12 characters")
            if getpass.getpass("Repeat password: ") != password:
                raise SystemExit("Passwords do not match")
            user = User(email=email, password_hash=passwords.hash(password))
            db.add(user)
            db.flush()
            audit(db, Actor(user.id, "OWNER"), "owner.created", target=user.id)
            db.commit()
            print("Owner created. Sign in through the web application.")
        else:
            if not db.get(Project, args.project_id):
                raise SystemExit("Project not found")
            registered = db.scalar(select(Agent).where(Agent.key == "domain-research"))
            registered.enabled = True
            token = secrets.token_urlsafe(48)
            db.add(
                AgentCredential(
                    agent_id=registered.id,
                    project_id=args.project_id,
                    token_hash=digest(token),
                    expires_at=now() + timedelta(hours=24),
                )
            )
            audit(
                db,
                Actor("local-operator", "OPERATOR"),
                "agent.credential_issued",
                project_id=args.project_id,
                target=registered.id,
            )
            db.commit()
            print("Project-scoped token, valid for 24 hours (shown once):")
            print(token)


if __name__ == "__main__":
    main()
