"""Read-only administrative queries and their audit records."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.errors import IntakeError
from . import contracts as c, mappers
from .models import AgentRun, AuditEvent, Conversation, Organization, ToolExecution, User
from .policies import AuditEventType
from .repository import audit, conversation_access, paginate, serialize

if TYPE_CHECKING:
    from .database import Database
    from .service import Platform


class AdminService:
    def __init__(self, database: Database, platform: Platform) -> None:
        self.database = database
        self.platform = platform

    def list_organizations(
        self, page: int, page_size: int, status: str | None
    ) -> c.PageDto[c.AdminOrganizationDto]:
        conditions = [Organization.status == status] if status else []
        with self.database.session() as db:
            result = paginate(db, Organization, conditions, page, page_size)
            return c.PageDto[c.AdminOrganizationDto].model_validate(result)

    def list_users(
        self,
        page: int,
        page_size: int,
        organization_id: str | None,
        status: str | None,
    ) -> c.PageDto[c.AdminUserDto]:
        conditions = []
        if organization_id:
            conditions.append(User.organization_id == organization_id)
        if status:
            conditions.append(User.status == status)
        with self.database.session() as db:
            result = paginate(db, User, conditions, page, page_size)
            return c.PageDto[c.AdminUserDto].model_validate(result)

    def list_conversations(
        self,
        page: int,
        page_size: int,
        organization_id: str | None,
        user_id: str | None,
        status: str | None,
    ) -> c.PageDto[c.AdminConversationDto]:
        conditions = []
        if organization_id:
            conditions.append(Conversation.organization_id == organization_id)
        if user_id:
            conditions.append(Conversation.owner_user_id == user_id)
        if status:
            conditions.append(Conversation.status == status)
        with self.database.session() as db:
            result = paginate(db, Conversation, conditions, page, page_size)
            return c.PageDto[c.AdminConversationDto].model_validate(result)

    def get_conversation(
        self, user: User, conversation_id: str, request_id: str
    ) -> c.AdminConversationDetailDto:
        with self.database.session.begin() as db:
            conversation = conversation_access(db, user, conversation_id, admin=True)
            audit(
                db,
                AuditEventType.ADMIN_CONVERSATION_VIEWED,
                user=user,
                request_id=request_id,
                conversation_id=conversation.id,
                metadata={"targetOwnerUserId": conversation.owner_user_id},
            )
            runs = db.scalars(
                select(AgentRun).where(AgentRun.conversation_id == conversation.id)
            ).all()
            tool_executions = db.scalars(
                select(ToolExecution).where(
                    ToolExecution.agent_run_id.in_([run.id for run in runs])
                )
            ).all()
            return c.AdminConversationDetailDto(
                conversation=serialize(conversation),
                user=serialize(db.get(User, conversation.owner_user_id)),
                organization=(
                    serialize(db.get(Organization, conversation.organization_id))
                    if conversation.organization_id
                    else None
                ),
                messages=self.platform.history(db, conversation.id),
                runs=[mappers.admin_run(db, run) for run in runs],
                toolExecutions=[serialize(item) for item in tool_executions],
            )

    def list_runs(
        self,
        page: int,
        page_size: int,
        *,
        conversation_id: str | None = None,
        status: str | None = None,
        scope_decision: str | None = None,
        error_code: str | None = None,
        tool_name: str | None = None,
        organization_id: str | None = None,
        user_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> c.PageDto[c.AdminAgentRunDto]:
        conditions: list[Any] = []
        for column, value in (
            (AgentRun.conversation_id, conversation_id),
            (AgentRun.status, status),
            (AgentRun.scope_decision, scope_decision),
            (AgentRun.error_code, error_code),
        ):
            if value:
                conditions.append(column == value)
        if tool_name:
            conditions.append(
                AgentRun.id.in_(
                    select(ToolExecution.agent_run_id).where(
                        ToolExecution.tool_name == tool_name
                    )
                )
            )
        if organization_id or user_id:
            conversations = select(Conversation.id)
            if organization_id:
                conversations = conversations.where(
                    Conversation.organization_id == organization_id
                )
            if user_id:
                conversations = conversations.where(
                    Conversation.owner_user_id == user_id
                )
            conditions.append(AgentRun.conversation_id.in_(conversations))
        if date_from:
            conditions.append(AgentRun.started_at >= date_from)
        if date_to:
            conditions.append(AgentRun.started_at <= date_to)

        with self.database.session() as db:
            result = paginate(db, AgentRun, conditions, page, page_size)
            result["items"] = [
                mappers.admin_run(db, db.get(AgentRun, item["id"]))
                for item in result["items"]
            ]
            return c.PageDto[c.AdminAgentRunDto].model_validate(result)

    def get_run(self, user: User, run_id: str, request_id: str) -> c.AdminRunDetailDto:
        with self.database.session.begin() as db:
            run = db.get(AgentRun, run_id)
            if run is None:
                raise IntakeError("RUN_NOT_FOUND", "La ejecución no existe.", 404)
            audit(
                db,
                AuditEventType.ADMIN_RUN_VIEWED,
                user=user,
                request_id=request_id,
                conversation_id=run.conversation_id,
                agent_run_id=run.id,
            )
            response = self.platform.run_response(db, run, admin=True)
            tools = db.scalars(
                select(ToolExecution)
                .where(ToolExecution.agent_run_id == run.id)
                .order_by(ToolExecution.sequence)
            ).all()
            response["toolExecutions"] = [serialize(item) for item in tools]
            return c.AdminRunDetailDto.model_validate(response)

    def list_audit_events(
        self,
        page: int,
        page_size: int,
        *,
        organization_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> c.PageDto[c.AdminAuditEventDto]:
        conditions = []
        for column, value in (
            (AuditEvent.organization_id, organization_id),
            (AuditEvent.conversation_id, conversation_id),
            (AuditEvent.actor_user_id, user_id),
            (AuditEvent.event_type, event_type),
        ):
            if value:
                conditions.append(column == value)
        if date_from:
            conditions.append(AuditEvent.created_at >= date_from)
        if date_to:
            conditions.append(AuditEvent.created_at <= date_to)
        with self.database.session() as db:
            result = paginate(db, AuditEvent, conditions, page, page_size)
            return c.PageDto[c.AdminAuditEventDto].model_validate(result)
