from pydantic import BaseModel, ConfigDict, JsonValue

from ..domain.models import ArticleRequestDraft, Attachment, DraftReviewAction


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str


class TranscriptionResponse(BaseModel):
    attachment: Attachment
    transcript: str


class IntakeStateUpdate(BaseModel):
    current_attachment_ids: list[str]
    current_request_draft_id: str


class AnalyzeAttachmentResponse(BaseModel):
    attachment: Attachment
    draft: ArticleRequestDraft
    state_update: IntakeStateUpdate


class ReviewFieldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    action: DraftReviewAction
    normalized_value: JsonValue = None
    required: bool | None = None
    note: str | None = None
