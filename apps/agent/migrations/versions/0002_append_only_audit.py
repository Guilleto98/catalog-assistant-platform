"""Enforce audit append-only at the database boundary."""

from alembic import op

revision = "0002_append_only_audit"
down_revision = "0001_platform"


def upgrade():
    op.execute("CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END")
    op.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END")


def downgrade():
    raise RuntimeError("Audit retention requires an explicit procedure.")
