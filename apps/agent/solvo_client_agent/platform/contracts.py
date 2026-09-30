"""Frozen V1 transport models: never serialize an ORM or ADK object to a client."""
from datetime import datetime, timezone
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from ..domain.models import AttachmentType, AttachmentStatus, DraftStatus, DraftFieldStatus


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def utc(cls, value):
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return value


class SafeError(DTO):
    code: str
    message: str


class HttpError(SafeError):
    requestId: str


class ApiError(DTO):
    error: HttpError


class OrganizationView(DTO):
    id: str
    name: str


class CurrentUserDto(DTO):
    id: str
    email: str
    role: Literal["CLIENT_USER", "INTERNAL_ADMIN"]
    organization: OrganizationView | None


class OkDto(DTO):
    ok: Literal[True] = True


class SearchFilter(DTO):
    field: str
    label: str
    operator: Literal["eq", "neq", "in", "contains", "gte", "lte", "between", "is_null"]
    value: JsonValue = None
    displayValue: str


class SearchSummary(DTO):
    filters: list[SearchFilter]


class ArticleListItem(DTO):
    code: str
    name: str | None = None
    species: str | None = None
    anatomicalGroup: str | None = None
    cut: str | None = None
    market: str | None = None
    destinationCountry: str | None = None
    temperature: str | None = None
    presentation: str | None = None
    primaryPackaging: str | None = None
    # Some Catalog results are projections. Unknown is not equivalent to false.
    active: bool | None = None


class ArticleSearchResultsPayload(DTO):
    query: SearchSummary | None
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1)
    articles: list[ArticleListItem]


class DisplayField(DTO):
    field: str
    label: str
    value: JsonValue
    displayValue: str


class ArticleGroup(DTO):
    key: str
    label: str
    fields: list[DisplayField]


class ArticleView(DTO):
    code: str
    name: str | None
    groups: list[ArticleGroup]


class ArticleDetailPayload(DTO):
    article: ArticleView


class ComparedArticle(DTO):
    code: str
    name: str | None = None


class ComparisonValue(DTO):
    articleCode: str
    value: JsonValue
    displayValue: str


class ComparisonRow(DTO):
    field: str
    label: str
    values: list[ComparisonValue]
    status: Literal["SAME", "DIFFERENT"]


class ArticleComparisonPayload(DTO):
    articles: list[ComparedArticle]
    rows: list[ComparisonRow]


class SimilarityCriterion(DTO):
    field: str
    label: str
    expectedValue: JsonValue
    expectedDisplayValue: str
    actualValue: JsonValue
    actualDisplayValue: str
    required: bool
    status: Literal["MATCH", "MISMATCH", "NOT_AVAILABLE"]


class UsedCriterion(DTO):
    field: str
    label: str
    value: JsonValue
    displayValue: str
    required: bool


class IgnoredCriterion(DTO):
    field: str
    label: str
    value: JsonValue = None
    reason: Literal["NOT_SUPPORTED_FOR_SIMILARITY", "UNCONFIRMED", "REJECTED", "NEEDS_CLARIFICATION", "OTHER"]


class SimilarityCandidate(DTO):
    article: ArticleListItem
    score: float = Field(ge=0, le=100)
    eligibility: Literal["ELIGIBLE", "INELIGIBLE"]
    criteria: list[SimilarityCriterion]


class SimilarityResultsPayload(DTO):
    mode: Literal["REFERENCE", "FEATURES", "DRAFT"]
    referenceArticleCode: str | None
    draftId: str | None
    usedCriteria: list[UsedCriterion]
    ignoredCriteria: list[IgnoredCriterion]
    eligibleCandidates: list[SimilarityCandidate]
    ineligibleCandidates: list[SimilarityCandidate]


class TechnicalSheetView(DTO):
    id: str
    articleCode: str
    title: str | None = None
    version: str | int | None = None
    language: str | None = None
    status: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    sourceNote: str | None = None
    documentAvailable: Literal[False] = False
    documentId: None = None


class TechnicalSheetPayload(DTO):
    sheet: TechnicalSheetView


class PdfSourceDto(DTO):
    type: Literal["PDF"]
    attachmentId: str
    page: int = Field(ge=1)


class SpreadsheetSourceDto(DTO):
    type: Literal["SPREADSHEET"]
    attachmentId: str
    sheet: str
    cell: str


class UserSourceDto(DTO):
    type: Literal["USER"]


SourceDto = Annotated[PdfSourceDto | SpreadsheetSourceDto | UserSourceDto, Field(discriminator="type")]


class DraftFieldDto(DTO):
    field: str
    label: str
    rawValue: JsonValue
    normalizedValue: JsonValue
    displayValue: str
    status: DraftFieldStatus
    required: bool
    source: SourceDto


class RequestDraftPayload(DTO):
    draftId: str
    status: DraftStatus
    fields: list[DraftFieldDto]
    updatedAt: datetime


class SavedFilterView(DTO):
    id: str
    name: str
    criteria: SearchSummary
    createdAt: datetime
    updatedAt: datetime


class SavedFilterListPayload(DTO):
    filters: list[SavedFilterView]


class SavedFilterCreatedPayload(DTO):
    filter: SavedFilterView


class SavedFilterDeletedPayload(DTO):
    id: str
    name: str


class AttachmentDto(DTO):
    id: str
    filename: str
    mimeType: str
    type: AttachmentType
    sizeBytes: int = Field(ge=0)
    status: AttachmentStatus
    createdAt: datetime
    error: SafeError | None
    transcription: str | None = None


class AttachmentStatusPayload(DTO):
    attachment: AttachmentDto


class ErrorUiPayload(SafeError):
    retryable: bool


class EventBase(DTO):
    id: str
    messageId: str
    schemaVersion: Literal[1] = 1
    sequence: int = Field(ge=1)
    createdAt: datetime


class SearchEvent(EventBase):
    type: Literal["ARTICLE_SEARCH_RESULTS"]
    payload: ArticleSearchResultsPayload


class DetailEvent(EventBase):
    type: Literal["ARTICLE_DETAIL"]
    payload: ArticleDetailPayload


class ComparisonEvent(EventBase):
    type: Literal["ARTICLE_COMPARISON"]
    payload: ArticleComparisonPayload


class SimilarityEvent(EventBase):
    type: Literal["SIMILARITY_RESULTS"]
    payload: SimilarityResultsPayload


class SheetEvent(EventBase):
    type: Literal["TECHNICAL_SHEET"]
    payload: TechnicalSheetPayload


class DraftEvent(EventBase):
    type: Literal["REQUEST_DRAFT"]
    payload: RequestDraftPayload


class FilterListEvent(EventBase):
    type: Literal["SAVED_FILTER_LIST"]
    payload: SavedFilterListPayload


class FilterCreatedEvent(EventBase):
    type: Literal["SAVED_FILTER_CREATED"]
    payload: SavedFilterCreatedPayload


class FilterDeletedEvent(EventBase):
    type: Literal["SAVED_FILTER_DELETED"]
    payload: SavedFilterDeletedPayload


class AttachmentEvent(EventBase):
    type: Literal["ATTACHMENT_STATUS"]
    payload: AttachmentStatusPayload


class ErrorEvent(EventBase):
    type: Literal["ERROR"]
    payload: ErrorUiPayload


UiEventDto = Annotated[SearchEvent | DetailEvent | ComparisonEvent | SimilarityEvent | SheetEvent |
    DraftEvent | FilterListEvent | FilterCreatedEvent | FilterDeletedEvent | AttachmentEvent | ErrorEvent,
    Field(discriminator="type")]


class AttachmentReferenceDto(DTO):
    id: str
    filename: str
    type: AttachmentType
    status: AttachmentStatus


class MessageDto(DTO):
    id: str
    conversationId: str
    role: Literal["USER", "ASSISTANT", "SYSTEM_EVENT"]
    messageType: Literal["TEXT", "AUDIO", "DOCUMENT", "SYSTEM"]
    text: str | None
    attachments: list[AttachmentReferenceDto]
    uiEvents: list[UiEventDto]
    createdAt: datetime


class ConversationSummaryDto(DTO):
    id: str
    title: str
    status: Literal["ACTIVE", "ARCHIVED"]
    preview: str | None
    createdAt: datetime
    updatedAt: datetime
    lastMessageAt: datetime | None


class AgentRunSummaryDto(DTO):
    id: str
    status: Literal["STARTED", "COMPLETED", "FAILED"]
    error: SafeError | None


class SendMessageResponse(DTO):
    userMessage: MessageDto
    assistantMessage: MessageDto | None
    run: AgentRunSummaryDto


class AnalyzeResponse(DTO):
    attachment: AttachmentDto
    draft: RequestDraftPayload


T = TypeVar("T")


class PageDto(DTO, Generic[T]):
    items: list[T]
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


# Admin V1 intentionally has a separate, safe inspection contract.
class AdminToolExecutionDto(DTO):
    id: str
    agent_run_id: str
    sequence: int
    tool_name: str
    arguments_json: dict[str, JsonValue]
    result_summary_json: dict[str, JsonValue] | None
    status: Literal["STARTED", "COMPLETED", "FAILED"]
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    error_code: str | None
    created_at: datetime


class AdminAgentRunDto(DTO):
    id: str
    conversation_id: str
    user_id: str
    organization_id: str | None
    user_message_id: str
    assistant_message_id: str | None
    status: Literal["STARTED", "COMPLETED", "FAILED"]
    provider: str
    model: str
    scope_decision: str | None
    scope_reason: str | None
    scope_latency_ms: float | None
    started_at: datetime
    completed_at: datetime | None
    latency_ms: float | None
    adk_invocation_id: str | None
    trace_id: str
    request_id: str
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: float | None
    error_code: str | None
    error_message_safe: str | None
    created_at: datetime


class AdminRunDetailDto(DTO):
    run: AdminAgentRunDto
    userMessage: MessageDto
    assistantMessage: MessageDto | None
    toolExecutions: list[AdminToolExecutionDto]


class AdminOrganizationDto(DTO):
    id: str
    name: str
    slug: str
    status: Literal["ACTIVE", "DISABLED"]
    created_at: datetime
    updated_at: datetime


class AdminUserDto(DTO):
    id: str
    organization_id: str | None
    email: str
    role: Literal["CLIENT_USER", "INTERNAL_ADMIN"]
    status: Literal["ACTIVE", "DISABLED"]
    catalog_demo_user_id: str | None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class AdminConversationDto(DTO):
    id: str
    organization_id: str | None
    owner_user_id: str
    title: str
    status: Literal["ACTIVE", "ARCHIVED"]
    adk_session_id: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    archived_at: datetime | None


class AdminConversationDetailDto(DTO):
    conversation: AdminConversationDto
    user: AdminUserDto
    organization: AdminOrganizationDto | None
    messages: list[MessageDto]
    runs: list[AdminAgentRunDto]
    toolExecutions: list[AdminToolExecutionDto]


class AdminAuditEventDto(DTO):
    id: str
    event_type: str
    actor_type: Literal["USER", "SYSTEM"]
    actor_user_id: str | None
    organization_id: str | None
    conversation_id: str | None
    agent_run_id: str | None
    entity_type: str | None
    entity_id: str | None
    request_id: str
    metadata_json: dict[str, JsonValue]
    created_at: datetime
