"""HTTP routes for health, legacy intake and authenticated intake workflows."""

from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile

from ..domain.errors import IntakeError
from ..domain.models import ArticleRequestDraft, Attachment
from ..platform import contracts as public
from ..platform.routes import require_active_conversation, require_conversation_access
from ..platform.models import User
from .schemas import AnalyzeAttachmentResponse, ErrorResponse, HealthResponse, ReviewFieldRequest, TranscriptionResponse

ERROR_RESPONSES = {
    status: {"model": ErrorResponse}
    for status in (
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
    )
}


def router() -> APIRouter:
    routes = APIRouter()

    @routes.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @routes.post(
        "/attachments", status_code=HTTPStatus.CREATED,
        response_model=Attachment, responses=ERROR_RESPONSES,
    )
    async def upload_attachment(
        request: Request,
        file: UploadFile = File(...),
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ) -> Attachment:
        conversation_id = _legacy_conversation(x_demo_conversation_id)
        return request.app.state.intake_service.upload(
            conversation_id, file.filename or "", file.content_type or "application/octet-stream", file.file
        )

    @routes.get("/attachments/{attachment_id}", response_model=Attachment, responses=ERROR_RESPONSES)
    async def get_attachment(
        attachment_id: str,
        request: Request,
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ) -> Attachment:
        return request.app.state.intake_service.get(
            attachment_id, _legacy_conversation(x_demo_conversation_id)
        )

    @routes.post("/attachments/{attachment_id}/transcribe", response_model=TranscriptionResponse,
                 responses=ERROR_RESPONSES)
    async def transcribe_attachment(
        attachment_id: str,
        request: Request,
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ) -> TranscriptionResponse:
        result = await request.app.state.intake_service.transcribe(
            attachment_id, _legacy_conversation(x_demo_conversation_id)
        )
        return TranscriptionResponse.model_validate(result)

    @routes.post("/attachments/{attachment_id}/analyze", status_code=HTTPStatus.CREATED,
                 response_model=AnalyzeAttachmentResponse, responses=ERROR_RESPONSES)
    async def analyze_attachment(
        attachment_id: str,
        request: Request,
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ) -> AnalyzeAttachmentResponse:
        result = await request.app.state.intake_service.analyze(
            attachment_id, _legacy_conversation(x_demo_conversation_id)
        )
        return AnalyzeAttachmentResponse.model_validate(result)

    @routes.get("/drafts/{draft_id}", response_model=ArticleRequestDraft, responses=ERROR_RESPONSES)
    async def get_draft(
        draft_id: str,
        request: Request,
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ):
        draft = request.app.state.intake_service.get_draft(
            draft_id, _legacy_conversation(x_demo_conversation_id)
        )
        return draft

    @routes.post("/drafts/{draft_id}/review", response_model=ArticleRequestDraft, responses=ERROR_RESPONSES)
    async def review_draft(
        draft_id: str,
        body: ReviewFieldRequest,
        request: Request,
        x_demo_conversation_id: Annotated[str | None, Header()] = None,
    ):
        return await request.app.state.intake_service.review_draft(
            draft_id, _legacy_conversation(x_demo_conversation_id), body
        )

    @routes.post("/conversations/{conversation_id}/attachments", status_code=HTTPStatus.CREATED,
                 response_model=public.AttachmentDto, tags=["attachments"], responses=ERROR_RESPONSES)
    async def product_upload(
        conversation_id: str,
        request: Request,
        file: UploadFile = File(...),
        user: User = Depends(require_active_conversation),
    ) -> public.AttachmentDto:
        return await request.app.state.intake_service.upload_for_conversation(
            request.app.state.platform, user, conversation_id, request.state.request_id,
            file.filename or "", file.content_type or "application/octet-stream", file.file,
        )

    @routes.get("/conversations/{conversation_id}/attachments/{attachment_id}",
                response_model=public.AttachmentDto, tags=["attachments"], responses=ERROR_RESPONSES)
    async def product_attachment(
        conversation_id: str,
        attachment_id: str,
        request: Request,
        _user: User = Depends(require_conversation_access),
    ) -> public.AttachmentDto:
        return request.app.state.intake_service.attachment_for_conversation(conversation_id, attachment_id)

    @routes.post("/conversations/{conversation_id}/attachments/{attachment_id}/transcribe",
                 response_model=public.AttachmentDto, tags=["attachments"], responses=ERROR_RESPONSES)
    async def product_transcribe(
        conversation_id: str,
        attachment_id: str,
        request: Request,
        user: User = Depends(require_active_conversation),
    ) -> public.AttachmentDto:
        return await request.app.state.intake_service.transcribe_for_conversation(
            request.app.state.platform, user, conversation_id, attachment_id, request.state.request_id
        )

    @routes.post("/conversations/{conversation_id}/attachments/{attachment_id}/analyze",
                 response_model=public.AnalyzeResponse, tags=["attachments"], responses=ERROR_RESPONSES)
    async def product_analyze(
        conversation_id: str,
        attachment_id: str,
        request: Request,
        user: User = Depends(require_active_conversation),
    ) -> public.AnalyzeResponse:
        return await request.app.state.intake_service.analyze_for_conversation(
            request.app.state.platform, user, conversation_id, attachment_id, request.state.request_id
        )

    @routes.get("/conversations/{conversation_id}/drafts/{draft_id}",
                response_model=public.RequestDraftPayload, tags=["drafts"], responses=ERROR_RESPONSES)
    async def product_draft(
        conversation_id: str,
        draft_id: str,
        request: Request,
        _user: User = Depends(require_conversation_access),
    ) -> public.RequestDraftPayload:
        return request.app.state.intake_service.draft_for_conversation(draft_id, conversation_id)

    @routes.post("/conversations/{conversation_id}/drafts/{draft_id}/review",
                 response_model=public.RequestDraftPayload, tags=["drafts"], responses=ERROR_RESPONSES)
    async def product_review(
        conversation_id: str,
        draft_id: str,
        body: ReviewFieldRequest,
        request: Request,
        user: User = Depends(require_active_conversation),
    ) -> public.RequestDraftPayload:
        return await request.app.state.intake_service.review_for_conversation(
            request.app.state.platform, user, conversation_id, draft_id, body, request.state.request_id
        )

    return routes


def _legacy_conversation(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    raise IntakeError("CONVERSATION_ID_REQUIRED", "Falta el encabezado X-Demo-Conversation-Id.", 400)
