"""Freeze public attachment references in the application database."""
from alembic import op
import sqlalchemy as sa

revision = "0004_attachment_snapshots"
down_revision = "0003_ui_event_snapshots"
branch_labels = depends_on = None


def upgrade():
    op.add_column("message_attachments", sa.Column("snapshot_json", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Historical references require an explicit migration policy")
