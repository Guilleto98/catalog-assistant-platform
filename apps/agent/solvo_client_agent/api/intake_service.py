"""Use cases for attachment intake and request-draft review."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, BinaryIO

from ..clients import CatalogApiError, get_catalog_api_client
from ..domain.errors import IntakeError
from ..domain.models import Attachment, AttachmentStatus, AttachmentType, DraftReviewAction
from ..platform import contracts as public
from ..platform import presenters
from ..platform.models import User
from ..platform.repository import audit, conversation_access
from .schemas import ReviewFieldRequest


class IntakeApplicationService:
    """Coordinates intake domain services and authenticated platform effects."""

    def __init__(self, container: Any) -> None:
        self.container = container

    def upload(self, conversation_id: str, filename: str, content_type: str, stream: BinaryIO) -> Attachment:
        return self.container.attachments.upload(conversation_id, filename, content_type, stream)

    def get(self, attachment_id: str, conversation_id: str) -> Attachment:
        return self.container.attachments.get(attachment_id, conversation_id)

    def get_draft(self, draft_id: str, conversation_id: str):
        return self.container.drafts.get(draft_id, conversation_id)

    async def transcribe(self, attachment_id: str, conversation_id: str) -> dict[str, Any]:
        attachment = self.get(attachment_id, conversation_id)
        self._require_type(attachment, {AttachmentType.AUDIO})
        self.container.attachments.update_status(attachment, AttachmentStatus.PROCESSING)
        try:
            text = await self.container.transcriber.transcribe(
                self.container.storage.path_for(attachment.filename)
            )
            attachment = attachment.model_copy(update={"transcription": text})
            ready = self.container.attachments.update_status(attachment, AttachmentStatus.READY)
            return {"attachment": ready.model_dump(mode="json"), "transcript": text}
        except IntakeError as error:
            self.container.attachments.update_status(attachment, AttachmentStatus.ERROR, error)
            raise

    async def analyze(self, attachment_id: str, conversation_id: str) -> dict[str, Any]:
        attachment = self.get(attachment_id, conversation_id)
        self._require_type(attachment, {AttachmentType.PDF, AttachmentType.SPREADSHEET})
        self.container.attachments.update_status(attachment, AttachmentStatus.PROCESSING)
        try:
            content, kind = self._parse_document(attachment)
            metadata = await get_catalog_api_client().get_filterable_fields()
            fields = await self.container.extraction.extract_fields(
                attachment.id, kind, content, metadata
            )
            draft = self.container.drafts.create(conversation_id, [attachment.id], fields)
            ready = self.container.attachments.update_status(attachment, AttachmentStatus.READY)
        except IntakeError as error:
            self.container.attachments.update_status(attachment, AttachmentStatus.ERROR, error)
            raise
        except CatalogApiError as error:
            intake_error = IntakeError(error.code, error.message, 502)
            self.container.attachments.update_status(attachment, AttachmentStatus.ERROR, intake_error)
            raise intake_error from error
        return {
            "attachment": ready.model_dump(mode="json"),
            "draft": draft.model_dump(mode="json"),
            "state_update": {"current_attachment_ids": [attachment.id], "current_request_draft_id": draft.id},
        }

    async def review_draft(
        self, draft_id: str, conversation_id: str, body: ReviewFieldRequest
    ):
        metadata = (
            await get_catalog_api_client().get_filterable_fields()
            if body.action == DraftReviewAction.CORRECT
            else []
        )
        field_metadata = self._find_field(metadata, body.field) if metadata else None
        if body.action == DraftReviewAction.CORRECT and field_metadata is None:
            raise IntakeError("INVALID_DRAFT_FIELD", "El campo no existe en el catálogo.", 422)
        return self.container.drafts.review_field(
            draft_id=draft_id,
            conversation_id=conversation_id,
            field_path=body.field,
            action=body.action,
            normalized_value=body.normalized_value,
            required=body.required,
            note=body.note,
            field_metadata=field_metadata,
        )

    async def upload_for_conversation(
        self, platform: Any, user: User, conversation_id: str, request_id: str,
        filename: str, content_type: str, stream: BinaryIO,
    ) -> public.AttachmentDto:
        result = self.upload(conversation_id, filename, content_type, stream)
        data = result.model_dump(mode="json")
        self._audit(platform, user, request_id, conversation_id, "ATTACHMENT_UPLOADED", result.id,
                    {"sizeBytes": data["size_bytes"], "type": data["type"]})
        return self._publish_attachment(platform, conversation_id, data)

    def attachment_for_conversation(
        self, conversation_id: str, attachment_id: str
    ) -> public.AttachmentDto:
        return presenters.attachment(self.get(attachment_id, conversation_id).model_dump(mode="json"))

    async def transcribe_for_conversation(
        self, platform: Any, user: User, conversation_id: str, attachment_id: str, request_id: str
    ) -> public.AttachmentDto:
        result = await self._process_product_attachment(
            platform, conversation_id, attachment_id, {AttachmentType.AUDIO},
            lambda: self.transcribe(attachment_id, conversation_id),
        )
        self._audit(platform, user, request_id, conversation_id, "ATTACHMENT_TRANSCRIBED", attachment_id)
        return self._publish_attachment(platform, conversation_id, result["attachment"])

    async def analyze_for_conversation(
        self, platform: Any, user: User, conversation_id: str, attachment_id: str, request_id: str
    ) -> public.AnalyzeResponse:
        result = await self._process_product_attachment(
            platform, conversation_id, attachment_id,
            {AttachmentType.PDF, AttachmentType.SPREADSHEET},
            lambda: self.analyze(attachment_id, conversation_id),
        )
        await self._persist_adk_state(platform, user, conversation_id, result["state_update"])
        self._audit(platform, user, request_id, conversation_id, "REQUEST_DRAFT_CREATED", result["draft"]["id"])
        draft = presenters.draft(result["draft"])
        attachment = self._publish_attachment(
            platform, conversation_id, result["attachment"], [("REQUEST_DRAFT", draft)]
        )
        return public.AnalyzeResponse(attachment=attachment, draft=draft)

    def draft_for_conversation(self, draft_id: str, conversation_id: str):
        return presenters.draft(self.get_draft(draft_id, conversation_id).model_dump(mode="json"))

    async def review_for_conversation(
        self, platform: Any, user: User, conversation_id: str, draft_id: str,
        body: ReviewFieldRequest, request_id: str,
    ):
        result = await self.review_draft(draft_id, conversation_id, body)
        event_type = (
            "REQUEST_DRAFT_CONFIRMED"
            if body.action == DraftReviewAction.CONFIRM
            else "REQUEST_DRAFT_UPDATED"
        )
        self._audit(platform, user, request_id, conversation_id, event_type, draft_id,
                    {"field": body.field, "action": body.action})
        draft = presenters.draft(result.model_dump(mode="json"))
        platform.system_events(conversation_id, [("REQUEST_DRAFT", draft)])
        return draft

    @staticmethod
    def _require_type(attachment: Attachment, allowed: set[AttachmentType]) -> None:
        if attachment.type in allowed:
            return
        if AttachmentType.AUDIO in allowed:
            raise IntakeError("ATTACHMENT_NOT_AUDIO", "El adjunto no es audio.", 422)
        raise IntakeError("ATTACHMENT_NOT_DOCUMENT", "El adjunto no es PDF ni XLSX.", 422)

    def _parse_document(self, attachment: Attachment) -> tuple[str, str]:
        path = self.container.storage.path_for(attachment.filename)
        if attachment.type == AttachmentType.PDF:
            return self.container.pdf.parse(path), "PDF"
        return self.container.spreadsheet.parse(path), "SPREADSHEET"

    @staticmethod
    def _find_field(metadata: list[dict[str, Any]], path: str) -> dict[str, Any] | None:
        return next((field for field in metadata if field.get("path") == path), None)

    async def _process_product_attachment(
        self,
        platform: Any,
        conversation_id: str,
        attachment_id: str,
        allowed: set[AttachmentType],
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        attachment = self.get(attachment_id, conversation_id)
        self._require_type(attachment, allowed)
        processing = self.container.attachments.update_status(attachment, AttachmentStatus.PROCESSING)
        self._publish_attachment(platform, conversation_id, processing.model_dump(mode="json"))
        try:
            return await operation()
        except Exception:
            attachment = self.get(attachment_id, conversation_id)
            if attachment.status != AttachmentStatus.ERROR:
                error = IntakeError(
                    "ATTACHMENT_PROCESSING_FAILED", "No se pudo procesar el adjunto.", 502
                )
                attachment = self.container.attachments.update_status(
                    attachment, AttachmentStatus.ERROR, error
                )
            self._publish_attachment(platform, conversation_id, attachment.model_dump(mode="json"))
            raise

    def _publish_attachment(
        self, platform: Any, conversation_id: str, data: dict[str, Any], extra: list[tuple[str, Any]] | None = None
    ) -> public.AttachmentDto:
        attachment = presenters.attachment(data)
        events = [("ATTACHMENT_STATUS", public.AttachmentStatusPayload(attachment=attachment))]
        platform.system_events(conversation_id, events + (extra or []), data["id"])
        return attachment

    @staticmethod
    def _audit(
        platform: Any, user: User, request_id: str, conversation_id: str, event_type: str,
        entity_id: str, metadata: dict[str, Any] | None = None,
    ) -> None:
        with platform.database.session.begin() as db:
            audit(db, event_type, user=user, request_id=request_id,
                  conversation_id=conversation_id, entity_id=entity_id, metadata=metadata)

    async def _persist_adk_state(
        self, platform: Any, user: User, conversation_id: str, state_delta: dict[str, Any]
    ) -> None:
        from google.adk.events import Event, EventActions

        with platform.database.session() as db:
            item = conversation_access(db, user, conversation_id)
        session = await platform.runtime.sessions.get_session(
            app_name=platform.runtime.app_name,
            user_id=f"app:{user.id}",
            session_id=item.adk_session_id,
        )
        await platform.runtime.sessions.append_event(
            session, Event(author="application", actions=EventActions(state_delta=state_delta))
        )
