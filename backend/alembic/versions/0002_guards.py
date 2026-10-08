"""Seed the registry and enforce PostgreSQL invariants with a limited runtime role."""

from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime, timezone

revision = "0002_guards"
down_revision = "49d1e6a7cff2"
branch_labels = None
depends_on = None


def upgrade():
    capabilities = json.dumps(["research:read", "research:submit"])
    capabilities_sql = "CAST(:capabilities AS JSONB)" if op.get_bind().dialect.name == "postgresql" else ":capabilities"
    op.execute(
        sa.text(
            f"INSERT INTO agents (id,key,name,enabled,capabilities,created_at) VALUES (:id,:key,:name,:enabled,{capabilities_sql},:created)"
        ).bindparams(
            id="00000000-0000-4000-8000-000000000001",
            key="domain-research",
            name="Domain Research",
            enabled=False,
            capabilities=capabilities,
            created=datetime.now(timezone.utc),
        )
    )
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
    CREATE FUNCTION guard_audit() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Audit events are append-only'; END; $$;
    CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION guard_audit();

    CREATE FUNCTION guard_candidate() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE run_state text; run_key varchar(36); count_candidates integer;
    BEGIN
      IF TG_OP = 'DELETE' THEN run_key := OLD.run_id; ELSE run_key := NEW.run_id; END IF;
      IF TG_OP = 'UPDATE' AND NEW.run_id <> OLD.run_id THEN RAISE EXCEPTION 'Cannot move candidate'; END IF;
      SELECT state INTO run_state FROM research_runs WHERE id=run_key FOR UPDATE;
      IF run_state <> 'RUNNING' THEN RAISE EXCEPTION 'Completed research is immutable'; END IF;
      IF TG_OP = 'INSERT' THEN
        SELECT count(*) INTO count_candidates FROM domain_candidates WHERE run_id=run_key;
        IF count_candidates >= 20 THEN RAISE EXCEPTION 'Maximum 20 candidates per run'; END IF;
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER candidate_guard BEFORE INSERT OR UPDATE OR DELETE ON domain_candidates
    FOR EACH ROW EXECUTE FUNCTION guard_candidate();

    CREATE FUNCTION guard_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE run_state text; candidate_key varchar(36);
    BEGIN
      IF TG_OP = 'DELETE' THEN candidate_key := OLD.candidate_id; ELSE candidate_key := NEW.candidate_id; END IF;
      IF TG_OP = 'UPDATE' AND NEW.candidate_id <> OLD.candidate_id THEN RAISE EXCEPTION 'Cannot move evidence'; END IF;
      SELECT r.state INTO run_state FROM research_runs r JOIN domain_candidates c ON c.run_id=r.id
        WHERE c.id=candidate_key FOR UPDATE OF r;
      IF run_state <> 'RUNNING' THEN RAISE EXCEPTION 'Completed evidence is immutable'; END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON research_evidence
    FOR EACH ROW EXECUTE FUNCTION guard_evidence();

    CREATE FUNCTION guard_run() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.state <> 'RUNNING' THEN RAISE EXCEPTION 'Finished runs are immutable'; END IF;
      IF TG_OP = 'UPDATE' AND (NEW.project_id <> OLD.project_id OR NEW.is_demo <> OLD.is_demo OR NEW.provider <> OLD.provider)
        THEN RAISE EXCEPTION 'Run provenance is immutable'; END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER run_guard BEFORE UPDATE OR DELETE ON research_runs
    FOR EACH ROW EXECUTE FUNCTION guard_run();

    CREATE FUNCTION guard_selection() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.status='BRAND_PENDING' THEN
        IF TG_OP='INSERT' OR OLD.status <> 'DOMAIN_SELECTION' THEN
          RAISE EXCEPTION 'Approval must transition from DOMAIN_SELECTION';
        END IF;
        IF NEW.selected_domain IS NULL OR NEW.selected_candidate_id IS NULL OR NEW.approved_by IS NULL OR NEW.approved_at IS NULL THEN
          RAISE EXCEPTION 'Approval attribution is required';
        END IF;
        IF NOT EXISTS(SELECT 1 FROM domain_candidates c JOIN research_runs r ON r.id=c.run_id
          WHERE c.id=NEW.selected_candidate_id AND r.project_id=NEW.id AND c.final_status='PASS'
          AND c.domain=NEW.selected_domain AND r.state='COMPLETED') THEN
          RAISE EXCEPTION 'Selection requires a PASS candidate from this project';
        END IF;
      ELSIF NEW.selected_domain IS NOT NULL OR NEW.selected_candidate_id IS NOT NULL OR NEW.approved_by IS NOT NULL OR NEW.approved_at IS NOT NULL THEN
        RAISE EXCEPTION 'Approval attribution requires BRAND_PENDING';
      END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER selection_guard BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION guard_selection();

    CREATE UNIQUE INDEX one_running_run_per_project ON research_runs(project_id) WHERE state='RUNNING';
    CREATE UNIQUE INDEX one_owner ON users(role);
    """)
    # Runtime role is provisioned by the database initialization script.
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='cc_app') THEN
        GRANT USAGE ON SCHEMA public TO cc_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON users,sessions,projects,agents,agent_credentials,research_runs,domain_candidates,research_evidence,approvals TO cc_app;
        GRANT SELECT, INSERT ON audit_events TO cc_app;
      END IF;
    END $$;
    """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table, trigger in [
            ("audit_events", "audit_immutable"),
            ("domain_candidates", "candidate_guard"),
            ("research_evidence", "evidence_guard"),
            ("research_runs", "run_guard"),
            ("projects", "selection_guard"),
        ]:
            op.execute(f"DROP TRIGGER {trigger} ON {table}")
        for function in [
            "guard_audit",
            "guard_candidate",
            "guard_evidence",
            "guard_run",
            "guard_selection",
        ]:
            op.execute(f"DROP FUNCTION {function}()")
        op.execute("DROP INDEX one_running_run_per_project")
        op.execute("DROP INDEX one_owner")
    op.execute("DELETE FROM agents WHERE id='00000000-0000-4000-8000-000000000001'")
