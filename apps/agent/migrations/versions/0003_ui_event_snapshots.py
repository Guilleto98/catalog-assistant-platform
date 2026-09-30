"""Persist explicit UI ordering and prevent historical event modification."""
from alembic import op
import sqlalchemy as sa

revision = "0003_ui_event_snapshots"
down_revision = "0002_append_only_audit"
branch_labels = depends_on = None


def upgrade():
    op.add_column("ui_events", sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"))
    op.execute("""UPDATE ui_events SET sequence = (
        SELECT COUNT(*) FROM ui_events AS earlier WHERE earlier.message_id=ui_events.message_id
        AND (earlier.created_at < ui_events.created_at OR
        (earlier.created_at=ui_events.created_at AND earlier.id <= ui_events.id)))""")
    op.create_index("ix_ui_event_message_sequence", "ui_events", ["message_id", "sequence"], unique=True)
    op.execute("CREATE TRIGGER ui_events_no_update BEFORE UPDATE ON ui_events BEGIN SELECT RAISE(ABORT, 'UI events are immutable'); END")
    op.execute("CREATE TRIGGER ui_events_no_delete BEFORE DELETE ON ui_events BEGIN SELECT RAISE(ABORT, 'UI events are immutable'); END")


def downgrade():
    raise RuntimeError("Immutable UI history requires an explicit retention/migration policy")
