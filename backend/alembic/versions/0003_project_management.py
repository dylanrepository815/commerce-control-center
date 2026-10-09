"""Allow Owner project rename and audited soft deletion."""

from alembic import op
import sqlalchemy as sa

revision = "0003_project_management"
down_revision = "0002_guards"
branch_labels = None
depends_on = None


def selection_guard(allow_existing_approval: bool):
    existing = (
        """
        IF OLD.status = 'BRAND_PENDING' AND NEW.status = 'BRAND_PENDING' THEN
          IF NEW.selected_domain IS DISTINCT FROM OLD.selected_domain
            OR NEW.selected_candidate_id IS DISTINCT FROM OLD.selected_candidate_id
            OR NEW.approved_by IS DISTINCT FROM OLD.approved_by
            OR NEW.approved_at IS DISTINCT FROM OLD.approved_at THEN
            RAISE EXCEPTION 'Approved domain and attribution are immutable';
          END IF;
          RETURN NEW;
        END IF;
        """
        if allow_existing_approval
        else ""
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION guard_selection()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          {existing}
          IF NEW.status='BRAND_PENDING' THEN
            IF TG_OP='INSERT' OR OLD.status <> 'DOMAIN_SELECTION' THEN
              RAISE EXCEPTION 'Approval must transition from DOMAIN_SELECTION';
            END IF;
            IF NEW.selected_domain IS NULL OR NEW.selected_candidate_id IS NULL
              OR NEW.approved_by IS NULL OR NEW.approved_at IS NULL THEN
              RAISE EXCEPTION 'Approval attribution is required';
            END IF;
            IF NOT EXISTS(
              SELECT 1 FROM domain_candidates c
              JOIN research_runs r ON r.id=c.run_id
              WHERE c.id=NEW.selected_candidate_id AND r.project_id=NEW.id
              AND c.final_status='PASS' AND c.domain=NEW.selected_domain
              AND r.state='COMPLETED') THEN
              RAISE EXCEPTION 'Selection requires a PASS candidate from this project';
            END IF;
          ELSIF NEW.selected_domain IS NOT NULL OR NEW.selected_candidate_id IS NOT NULL
            OR NEW.approved_by IS NOT NULL OR NEW.approved_at IS NOT NULL THEN
            RAISE EXCEPTION 'Approval attribution requires BRAND_PENDING';
          END IF;
          RETURN NEW;
        END; $$;
        """
    )


def upgrade():
    op.add_column("projects", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"])
    if op.get_bind().dialect.name == "postgresql":
        selection_guard(True)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        selection_guard(False)
    op.drop_index("ix_projects_deleted_at", "projects")
    op.drop_column("projects", "deleted_at")
