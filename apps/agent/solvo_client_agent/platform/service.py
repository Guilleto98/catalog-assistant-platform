"""Conversation lifecycle and durable message/run coordination."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..clients import get_catalog_api_client
from ..domain.errors import IntakeError
from .auth import AuthService
from .context import catalog_identity, intake_drafts
from .database import Database
from ..domain.models import Attachment, AttachmentStatus, AttachmentType
from .models import (
    AgentRun,
    Conversation,
    Message,
    MessageAttachmentReference,
    ToolExecution,
    UiEvent,
    User,
    now,
)
from .policies import (
    AccountRole,
    AgentRunStatus,
    AuditEventType,
    ConversationStatus,
    MessageRole,
    RequestLimits,
    MessageType,
    ToolExecutionStatus,
)
from .repository import audit, conversation_access, paginate, serialize
from .runtime import AgentRuntime, ToolAuditPlugin
from .requests import SendMessageRequest
from .admin_service import AdminService
from . import contracts as c, mappers, presenters

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..api.app import Container
    from ..config import Settings


class Platform:
    def __init__(
        self,
        settings: Settings,
        intake: Container,
        runtime: AgentRuntime | None = None,
    ) -> None:
        self.settings, self.intake = settings, intake
        self.database = Database(settings.application_database_path or settings.intake_database_path.parent / "application.db")
        self.auth = AuthService(self.database, settings)
        self.runtime = runtime or AgentRuntime(settings.adk_database_path or settings.intake_database_path.parent / "adk_sessions.db")
        self.admin = AdminService(self.database, self)

    def authenticate(self, token: str | None) -> User:
        return self.auth.authenticate(token)

    def require_internal_admin(self, user: User) -> User:
        if user.role != AccountRole.INTERNAL_ADMIN:
            raise IntakeError("FORBIDDEN", "Acceso no permitido.", 403)
        return user

    def require_conversation_access(self, user: User, conversation_id: str) -> User:
        with self.database.session() as db:
            conversation_access(db, user, conversation_id)
        return user

    def require_active_conversation(self, user: User, conversation_id: str) -> User:
        with self.database.session() as db:
            conversation = conversation_access(db, user, conversation_id)
            if conversation.status != ConversationStatus.ACTIVE:
                raise IntakeError("CONVERSATION_ARCHIVED", "La conversación está archivada.", 409)
        return user

    def current_user(self, user: User) -> c.CurrentUserDto:
        with self.database.session() as db:
            return mappers.current_user(db, user)

    async def saved_filters(self, user: User) -> c.SavedFilterListPayload:
        if not user.catalog_demo_user_id:
            return c.SavedFilterListPayload(filters=[])
        rows = await get_catalog_api_client().list_saved_filters(user_id=user.catalog_demo_user_id)
        return c.SavedFilterListPayload(filters=[presenters.saved_filter(row) for row in rows])

    async def create_conversation(
        self, user: User, request_id: str
    ) -> c.ConversationSummaryDto:
        conversation_id = str(uuid4())
        session_id = await self.runtime.create_session(user.id, conversation_id)
        with self.database.session.begin() as db:
            item = Conversation(id=conversation_id, organization_id=user.organization_id,
                                owner_user_id=user.id, adk_session_id=session_id)
            db.add(item)
            db.flush()
            audit(db, AuditEventType.CONVERSATION_CREATED, user=user, request_id=request_id,
                  conversation_id=item.id, entity_type="Conversation", entity_id=item.id)
        with self.database.session() as db:
            return mappers.conversation(db, item)

    def list_conversations(
        self, user: User, page: int, page_size: int
    ) -> c.PageDto[c.ConversationSummaryDto]:
        conditions = [
            Conversation.owner_user_id == user.id,
            Conversation.organization_id == user.organization_id,
        ]
        with self.database.session() as db:
            query = select(Conversation).where(*conditions)
            total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
            items = db.scalars(
                query.order_by(
                    func.coalesce(
                        Conversation.last_message_at, Conversation.created_at
                    ).desc(),
                    Conversation.id,
                )
                .offset((page - RequestLimits.PAGE_INDEX_ORIGIN) * page_size)
                .limit(page_size)
            )
            return c.PageDto[c.ConversationSummaryDto](
                items=[mappers.conversation(db, item) for item in items],
                page=page,
                pageSize=page_size,
                total=total,
            )

    def get_conversation(
        self, user: User, conversation_id: str
    ) -> c.ConversationSummaryDto:
        with self.database.session() as db:
            item = conversation_access(db, user, conversation_id)
            return mappers.conversation(db, item)

    def list_messages(
        self, user: User, conversation_id: str, page: int, page_size: int
    ) -> c.PageDto[c.MessageDto]:
        with self.database.session() as db:
            conversation_access(db, user, conversation_id)
            result = paginate(
                db,
                Message,
                [Message.conversation_id == conversation_id],
                page,
                page_size,
                ascending=True,
            )
            message_ids = {row["id"] for row in result["items"]}
            result["items"] = self.history(db, conversation_id, message_ids)
            return c.PageDto[c.MessageDto].model_validate(result)

    def archive_conversation(
        self, user: User, conversation_id: str, request_id: str
    ) -> c.ConversationSummaryDto:
        with self.database.session.begin() as db:
            item = conversation_access(db, user, conversation_id)
            if item.status != ConversationStatus.ARCHIVED:
                item.status = ConversationStatus.ARCHIVED
                item.archived_at = item.updated_at = now()
                audit(
                    db,
                    AuditEventType.CONVERSATION_ARCHIVED,
                    user=user,
                    request_id=request_id,
                    conversation_id=item.id,
                )
            return mappers.conversation(db, item)

    def history(
        self,
        db: Session,
        conversation_id: str,
        message_ids: set[str] | None = None,
    ) -> list[c.MessageDto]:
        query = select(Message).where(Message.conversation_id == conversation_id)
        if message_ids is not None:
            query = query.where(Message.id.in_(message_ids))
        messages = db.scalars(query.order_by(Message.created_at, Message.id)).all()
        result = []
        for message in messages:
            result.append(self.message_dto(db, message))
        return result

    def message_dto(self, db: Session, message: Message) -> c.MessageDto:
        refs = []
        for reference in db.scalars(select(MessageAttachmentReference).where(
                MessageAttachmentReference.message_id == message.id).order_by(MessageAttachmentReference.attachment_id)):
            if reference.snapshot_json is not None:
                refs.append(c.AttachmentReferenceDto.model_validate(reference.snapshot_json))
            else:
                # Only pre-V1 references lack a snapshot. No catalog/model needed.
                item = self.intake.attachments.get(reference.attachment_id, message.conversation_id)
                refs.append(c.AttachmentReferenceDto(id=item.id, filename=item.original_filename, type=item.type, status=item.status))
        events = [presenters.EVENT_ADAPTER.validate_python({"id": v.id, "messageId": v.message_id, "type": v.type,
            "schemaVersion": v.schema_version, "sequence": v.sequence, "payload": v.payload_json, "createdAt": v.created_at})
            for v in db.scalars(select(UiEvent).where(UiEvent.message_id == message.id).order_by(UiEvent.sequence))]
        return c.MessageDto(id=message.id, conversationId=message.conversation_id, role=message.role,
            messageType=message.message_type, text=message.content_text, attachments=refs, uiEvents=events, createdAt=message.created_at)

    def run_response(
        self, db: Session, run: AgentRun, *, admin: bool = False
    ) -> dict[str, Any]:
        error = c.SafeError(code=run.error_code, message=run.error_message_safe) if run.error_code else None
        return {"run": mappers.admin_run(db, run) if admin else c.AgentRunSummaryDto(id=run.id, status=run.status, error=error),
                "userMessage": self.message_dto(db, db.get(Message, run.user_message_id)),
                "assistantMessage": self.message_dto(db, db.get(Message, run.assistant_message_id)) if run.assistant_message_id else None}

    def persist_events(
        self, db: Session, message: Message, events: list[tuple[str, Any]]
    ) -> None:
        for sequence, (kind, payload) in enumerate(
            events, RequestLimits.PAGE_INDEX_ORIGIN
        ):
            validated = presenters.EVENTS[kind].model_validate(payload)
            db.add(UiEvent(message_id=message.id, type=kind, schema_version=1, sequence=sequence,
                           payload_json=validated.model_dump(mode="json")))
        db.flush()

    def system_events(
        self,
        conversation_id: str,
        events: list[tuple[str, Any]],
        attachment_id: str | None = None,
    ) -> c.MessageDto:
        with self.database.session.begin() as db:
            message = Message(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM_EVENT,
                message_type=MessageType.SYSTEM,
                content_text=None,
            )
            db.add(message)
            db.flush()
            if attachment_id:
                item = self.intake.attachments.get(attachment_id, conversation_id)
                snapshot = c.AttachmentReferenceDto(id=item.id, filename=item.original_filename, type=item.type, status=item.status)
                db.add(MessageAttachmentReference(message_id=message.id, attachment_id=attachment_id,
                    snapshot_json=snapshot.model_dump(mode="json")))
            self.persist_events(db, message, events)
            conversation = db.get(Conversation, conversation_id)
            conversation.last_message_at = conversation.updated_at = now()
            return self.message_dto(db, message)

    async def send_message(
        self,
        user: User,
        conversation_id: str,
        body: SendMessageRequest,
        request_id: str,
    ) -> c.SendMessageResponse:
        started = time.perf_counter()
        existing_response = self._idempotent_response(user, conversation_id, body)
        if existing_response is not None:
            return existing_response

        attachments = self._load_ready_attachments(body.attachment_ids, conversation_id)
        effective_text = self._effective_message_text(body.text, attachments)
        conversation, run = self._persist_user_message(
            user, conversation_id, body, attachments, request_id
        )
        return await self._execute_agent_run(
            user,
            conversation,
            run,
            effective_text,
            request_id,
            started,
        )

    def _idempotent_response(
        self,
        user: User,
        conversation_id: str,
        body: SendMessageRequest,
    ) -> c.SendMessageResponse | None:
        with self.database.session() as db:
            conversation_access(db, user, conversation_id)
            previous = db.scalar(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.client_message_id == body.client_message_id,
                )
            )
            if previous is None:
                return None
            self._validate_idempotent_retry(db, previous, body)
            run = db.scalar(
                select(AgentRun).where(AgentRun.user_message_id == previous.id)
            )
            if run is None:
                raise IntakeError(
                    "MESSAGE_STATE_INCOMPLETE",
                    "El mensaje está guardado, pero su ejecución no está disponible.",
                    409,
                )
            return c.SendMessageResponse.model_validate(self.run_response(db, run))

    @staticmethod
    def _validate_idempotent_retry(
        db: Session, previous: Message, body: SendMessageRequest
    ) -> None:
        attachment_ids = list(
            db.scalars(
                select(MessageAttachmentReference.attachment_id).where(
                    MessageAttachmentReference.message_id == previous.id
                )
            )
        )
        if (
            previous.content_text != body.text
            or sorted(attachment_ids) != sorted(body.attachment_ids)
        ):
            raise IntakeError(
                "MESSAGE_DUPLICATE",
                "El identificador ya corresponde a otro mensaje.",
                409,
            )

    def _load_ready_attachments(
        self, attachment_ids: list[str], conversation_id: str
    ) -> list[Attachment]:
        attachments = []
        for attachment_id in attachment_ids:
            try:
                attachment = self.intake.attachments.get(attachment_id, conversation_id)
            except IntakeError as error:
                raise IntakeError(
                    "ATTACHMENT_ACCESS_DENIED",
                    "El adjunto no está disponible en esta conversación.",
                    403,
                ) from error
            if attachment.status != AttachmentStatus.READY:
                raise IntakeError(
                    "ATTACHMENT_NOT_READY",
                    "Procesá el adjunto antes de enviar el mensaje.",
                    409,
                )
            attachments.append(attachment)
        return attachments

    @staticmethod
    def _effective_message_text(
        text: str | None, attachments: list[Attachment]
    ) -> str:
        if text:
            return text
        return "\n".join(
            attachment.transcription or "Consultá el borrador del documento adjunto."
            for attachment in attachments
        )

    def _persist_user_message(
        self,
        user: User,
        conversation_id: str,
        body: SendMessageRequest,
        attachments: list[Attachment],
        request_id: str,
    ) -> tuple[Conversation, AgentRun]:
        provider, _, model = self.settings.model.partition("/")
        try:
            with self.database.session.begin() as db:
                conversation = conversation_access(db, user, conversation_id)
                if conversation.status != ConversationStatus.ACTIVE:
                    raise IntakeError(
                        "CONVERSATION_ARCHIVED",
                        "La conversación está archivada.",
                        409,
                    )
                message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content_text=body.text,
                    client_message_id=body.client_message_id,
                    message_type=self._message_type(attachments),
                )
                db.add(message)
                db.flush()
                self._persist_attachment_references(db, message, attachments)
                run = AgentRun(
                    conversation_id=conversation_id,
                    user_message_id=message.id,
                    provider=provider,
                    model=model or provider,
                    trace_id=str(uuid4()),
                    request_id=request_id,
                )
                db.add(run)
                db.flush()
                self._audit_run_started(db, user, request_id, conversation_id, message, run)
                self._set_first_conversation_title(db, conversation, message, body, attachments)
                conversation.last_message_at = conversation.updated_at = now()
                return conversation, run
        except IntegrityError as error:
            raise IntakeError(
                "MESSAGE_IN_PROGRESS",
                "Hay un mensaje en proceso; consultá su estado antes de reintentar.",
                409,
            ) from error

    @staticmethod
    def _message_type(attachments: list[Attachment]) -> MessageType:
        if not attachments:
            return MessageType.TEXT
        if all(item.type == AttachmentType.AUDIO for item in attachments):
            return MessageType.AUDIO
        return MessageType.DOCUMENT

    @staticmethod
    def _persist_attachment_references(
        db: Session, message: Message, attachments: list[Attachment]
    ) -> None:
        for item in attachments:
            snapshot = c.AttachmentReferenceDto(
                id=item.id,
                filename=item.original_filename,
                type=item.type,
                status=item.status,
            )
            db.add(
                MessageAttachmentReference(
                    message_id=message.id,
                    attachment_id=item.id,
                    snapshot_json=snapshot.model_dump(mode="json"),
                )
            )

    @staticmethod
    def _audit_run_started(
        db: Session,
        user: User,
        request_id: str,
        conversation_id: str,
        message: Message,
        run: AgentRun,
    ) -> None:
        audit(
            db,
            AuditEventType.USER_MESSAGE_CREATED,
            user=user,
            request_id=request_id,
            conversation_id=conversation_id,
            entity_type="Message",
            entity_id=message.id,
        )
        audit(
            db,
            AuditEventType.AGENT_RUN_STARTED,
            user=user,
            request_id=request_id,
            conversation_id=conversation_id,
            agent_run_id=run.id,
        )

    @staticmethod
    def _set_first_conversation_title(
        db: Session,
        conversation: Conversation,
        message: Message,
        body: SendMessageRequest,
        attachments: list[Attachment],
    ) -> None:
        previous_message_id = db.scalar(
            select(Message.id)
            .where(
                Message.conversation_id == conversation.id,
                Message.role == MessageRole.USER,
                Message.id != message.id,
            )
            .limit(RequestLimits.PAGE_INDEX_ORIGIN)
        )
        if previous_message_id is None:
            title = body.text or attachments[0].original_filename
            conversation.title = title[: RequestLimits.CONVERSATION_TITLE_CHARACTERS]

    async def _execute_agent_run(
        self,
        user: User,
        conversation: Conversation,
        run: AgentRun,
        effective_text: str,
        request_id: str,
        started: float,
    ) -> c.SendMessageResponse:
        plugin = ToolAuditPlugin(
            self.database, run.id, user, request_id, conversation.id
        )
        logger.info(
            "agent_run request_id=%s conversation_id=%s agent_run_id=%s status=%s",
            request_id,
            conversation.id,
            run.id,
            AgentRunStatus.STARTED,
        )
        identity_token = catalog_identity.set(user.catalog_demo_user_id)
        drafts_token = intake_drafts.set(self.intake.drafts)
        try:
            outcome = await self.runtime.execute(
                user, conversation, effective_text, plugin
            )
            return self._persist_agent_success(
                user, conversation.id, run.id, outcome, plugin, request_id, started
            )
        except Exception as error:
            await self._persist_agent_failure(
                user, conversation, run.id, request_id, started
            )
            raise IntakeError(
                "AGENT_EXECUTION_FAILED",
                "No se pudo completar la respuesta del agente.",
                502,
            ) from error
        finally:
            catalog_identity.reset(identity_token)
            intake_drafts.reset(drafts_token)

    def _persist_agent_success(
        self,
        user: User,
        conversation_id: str,
        run_id: str,
        outcome: dict[str, Any],
        plugin: ToolAuditPlugin,
        request_id: str,
        started: float,
    ) -> c.SendMessageResponse:
        with self.database.session.begin() as db:
            assistant = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content_text=outcome["text"],
            )
            db.add(assistant)
            db.flush()
            persistence_started = time.perf_counter()
            final_events = presenters.final_events(plugin.ui_events)
            self.persist_events(db, assistant, final_events)
            persistence_ms = (time.perf_counter() - persistence_started) * 1000
            current = db.get(AgentRun, run_id)
            state = outcome.get("state", {})
            current.assistant_message_id = assistant.id
            current.status = AgentRunStatus.COMPLETED
            current.adk_invocation_id = outcome.get("invocation_id")
            current.input_tokens = outcome.get("input_tokens")
            current.output_tokens = outcome.get("output_tokens")
            current.scope_decision = state.get("domain_scope_decision")
            current.scope_reason = state.get("domain_scope_reason")
            current.scope_latency_ms = state.get("domain_scope_latency_ms")
            current.completed_at = now()
            current.latency_ms = (time.perf_counter() - started) * 1000
            conversation = db.get(Conversation, conversation_id)
            conversation.updated_at = conversation.last_message_at = now()
            self._audit_run_completed(
                db, user, request_id, conversation_id, current, len(final_events),
                plugin.presenter_latency_ms, persistence_ms,
            )
            response = c.SendMessageResponse.model_validate(self.run_response(db, current))
        logger.info(
            "agent_run request_id=%s conversation_id=%s agent_run_id=%s status=%s duration_ms=%.1f",
            request_id,
            conversation_id,
            run_id,
            AgentRunStatus.COMPLETED,
            current.latency_ms,
        )
        return response

    @staticmethod
    def _audit_run_completed(
        db: Session,
        user: User,
        request_id: str,
        conversation_id: str,
        run: AgentRun,
        event_count: int,
        presenter_latency_ms: float,
        persistence_ms: float,
    ) -> None:
        audit(
            db,
            AuditEventType.AGENT_RUN_COMPLETED,
            user=user,
            request_id=request_id,
            conversation_id=conversation_id,
            agent_run_id=run.id,
            metadata={
                "uiEventCount": event_count,
                "presenterLatencyMs": round(presenter_latency_ms, 3),
                "uiPersistenceFlushMs": round(persistence_ms, 3),
            },
        )

    async def _persist_agent_failure(
        self,
        user: User,
        conversation: Conversation,
        run_id: str,
        request_id: str,
        started: float,
    ) -> None:
        state = await self._runtime_state(user, conversation)
        with self.database.session.begin() as db:
            current = db.get(AgentRun, run_id)
            current.status = AgentRunStatus.FAILED
            current.error_code = "AGENT_EXECUTION_FAILED"
            current.error_message_safe = "No se pudo completar la respuesta del agente."
            current.completed_at = now()
            current.latency_ms = (time.perf_counter() - started) * 1000
            current.scope_decision = state.get("domain_scope_decision")
            current.scope_reason = state.get("domain_scope_reason")
            current.scope_latency_ms = state.get("domain_scope_latency_ms")
            for tool in db.scalars(
                select(ToolExecution).where(
                    ToolExecution.agent_run_id == run_id,
                    ToolExecution.status == ToolExecutionStatus.STARTED,
                )
            ):
                tool.status = ToolExecutionStatus.FAILED
                tool.error_code = current.error_code
                tool.completed_at = now()
            audit(
                db,
                AuditEventType.AGENT_RUN_FAILED,
                user=user,
                request_id=request_id,
                conversation_id=conversation.id,
                agent_run_id=run_id,
                metadata={"errorCode": current.error_code},
            )

    async def _runtime_state(
        self, user: User, conversation: Conversation
    ) -> dict[str, Any]:
        try:
            session = await self.runtime.sessions.get_session(
                app_name=self.runtime.app_name,
                user_id=f"app:{user.id}",
                session_id=conversation.adk_session_id,
            )
        except Exception:
            return {}
        return session.state if session else {}

    async def close(self):
        await self.runtime.close()
        self.database.close()
