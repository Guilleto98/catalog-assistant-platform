"""Product records, independent of ADK and Catalog tables."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def identifier() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Organization(Record, Base):
    __tablename__ = "organizations"
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(default="ACTIVE")
    updated_at: Mapped[datetime] = mapped_column(default=now)


class User(Record, Base):
    __tablename__ = "users"
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[str]
    status: Mapped[str] = mapped_column(default="ACTIVE")
    catalog_demo_user_id: Mapped[str | None]
    updated_at: Mapped[datetime] = mapped_column(default=now)
    last_login_at: Mapped[datetime | None]


class AuthSession(Record, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    last_seen_at: Mapped[datetime] = mapped_column(default=now)
    revoked_at: Mapped[datetime | None]


class Conversation(Record, Base):
    __tablename__ = "conversations"
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(default="Nueva conversación")
    status: Mapped[str] = mapped_column(default="ACTIVE")
    adk_session_id: Mapped[str] = mapped_column(unique=True)
    updated_at: Mapped[datetime] = mapped_column(default=now, index=True)
    last_message_at: Mapped[datetime | None]
    archived_at: Mapped[datetime | None]


class Message(Record, Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "client_message_id"),)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str]
    message_type: Mapped[str] = mapped_column(default="TEXT")
    content_text: Mapped[str | None]
    client_message_id: Mapped[str | None]


class MessageAttachmentReference(Base):
    __tablename__ = "message_attachments"
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), primary_key=True)
    attachment_id: Mapped[str] = mapped_column(primary_key=True)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON)


class AgentRun(Record, Base):
    __tablename__ = "agent_runs"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    user_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True)
    assistant_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"))
    status: Mapped[str] = mapped_column(default="STARTED", index=True)
    provider: Mapped[str]
    model: Mapped[str]
    scope_decision: Mapped[str | None]
    scope_reason: Mapped[str | None]
    scope_latency_ms: Mapped[float | None]
    started_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None]
    latency_ms: Mapped[float | None]
    adk_invocation_id: Mapped[str | None]
    trace_id: Mapped[str]
    request_id: Mapped[str]
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    estimated_cost: Mapped[float | None]
    error_code: Mapped[str | None]
    error_message_safe: Mapped[str | None]


class ToolExecution(Record, Base):
    __tablename__ = "tool_executions"
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    sequence: Mapped[int]
    tool_name: Mapped[str]
    arguments_json: Mapped[dict] = mapped_column(JSON)
    result_summary_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(default="STARTED")
    started_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None]
    duration_ms: Mapped[float | None]
    error_code: Mapped[str | None]


class UiEvent(Record, Base):
    __tablename__ = "ui_events"
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    type: Mapped[str]
    schema_version: Mapped[int] = mapped_column(default=1)
    sequence: Mapped[int]
    payload_json: Mapped[dict] = mapped_column(JSON)


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_created_at", "created_at"),)
    event_type: Mapped[str]
    actor_type: Mapped[str] = mapped_column(default="USER")
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    entity_type: Mapped[str | None]
    entity_id: Mapped[str | None]
    request_id: Mapped[str]
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
