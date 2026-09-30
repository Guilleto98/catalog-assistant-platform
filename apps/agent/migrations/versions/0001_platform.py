"""Initial immutable product schema."""

from alembic import op
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy import text

revision = "0001_platform"
down_revision = None


def upgrade():
    def table(name, *columns, **kwargs):
        op.create_table(name, Column("id", String(36), primary_key=True), Column("created_at", DateTime, nullable=False), *columns, **kwargs)

    def col(name, kind=String, nullable=False, fk=None):
        return Column(name, kind, *([ForeignKey(fk)] if fk else []), nullable=nullable)

    table("organizations", col("name"), col("slug"), col("status"), col("updated_at", DateTime), UniqueConstraint("slug"))
    table("users", col("organization_id", nullable=True, fk="organizations.id"), col("email"), col("password_hash"), col("role"), col("status"), col("catalog_demo_user_id", nullable=True), col("updated_at", DateTime), col("last_login_at", DateTime, True), UniqueConstraint("email"))
    table("auth_sessions", col("user_id", fk="users.id"), col("token_hash"), col("expires_at", DateTime), col("last_seen_at", DateTime), col("revoked_at", DateTime, True), UniqueConstraint("token_hash"))
    table("conversations", col("organization_id", nullable=True, fk="organizations.id"), col("owner_user_id", fk="users.id"), col("title"), col("status"), col("adk_session_id"), col("updated_at", DateTime), col("last_message_at", DateTime, True), col("archived_at", DateTime, True), UniqueConstraint("adk_session_id"))
    table("messages", col("conversation_id", fk="conversations.id"), col("role"), col("message_type"), col("content_text", nullable=True), col("client_message_id", nullable=True), UniqueConstraint("conversation_id", "client_message_id"))
    op.create_table("message_attachments", Column("message_id", String, ForeignKey("messages.id"), primary_key=True), Column("attachment_id", String, primary_key=True))
    table("agent_runs", col("conversation_id", fk="conversations.id"), col("user_message_id", fk="messages.id"), col("assistant_message_id", nullable=True, fk="messages.id"), col("status"), col("provider"), col("model"), col("scope_decision", nullable=True), col("scope_reason", nullable=True), col("scope_latency_ms", Float, True), col("started_at", DateTime), col("completed_at", DateTime, True), col("latency_ms", Float, True), col("adk_invocation_id", nullable=True), col("trace_id"), col("request_id"), col("input_tokens", Integer, True), col("output_tokens", Integer, True), col("estimated_cost", Float, True), col("error_code", nullable=True), col("error_message_safe", nullable=True), UniqueConstraint("user_message_id"))
    table("tool_executions", col("agent_run_id", fk="agent_runs.id"), col("sequence", Integer), col("tool_name"), col("arguments_json", JSON), col("result_summary_json", JSON, True), col("status"), col("started_at", DateTime), col("completed_at", DateTime, True), col("duration_ms", Float, True), col("error_code", nullable=True))
    op.create_index("one_active_run_per_conversation", "agent_runs", ["conversation_id"], unique=True, sqlite_where=text("status = 'STARTED'"))
    table("ui_events", col("message_id", fk="messages.id"), col("type"), col("schema_version", Integer), col("payload_json", JSON))
    table("audit_events", col("event_type"), col("actor_type"), col("actor_user_id", nullable=True, fk="users.id"), col("organization_id", nullable=True, fk="organizations.id"), col("conversation_id", nullable=True, fk="conversations.id"), col("agent_run_id", nullable=True, fk="agent_runs.id"), col("entity_type", nullable=True), col("entity_id", nullable=True), col("request_id"), col("metadata_json", JSON))
    for name, columns in {
        "users": ["organization_id"], "auth_sessions": ["user_id"],
        "conversations": ["organization_id", "owner_user_id", "updated_at"],
        "messages": ["conversation_id"], "agent_runs": ["conversation_id", "status"],
        "tool_executions": ["agent_run_id"], "ui_events": ["message_id"],
        "audit_events": ["created_at", "organization_id", "conversation_id"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{name}_{column}", name, [column])


def downgrade():
    raise RuntimeError("Platform history requires an explicit retention procedure; downgrade is disabled.")
