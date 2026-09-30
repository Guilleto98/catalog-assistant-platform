"""Validated domain contracts. Binary data is deliberately never represented here."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AttachmentType(StrEnum):
    AUDIO = "AUDIO"
    PDF = "PDF"
    SPREADSHEET = "SPREADSHEET"


class AttachmentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"


class Attachment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    filename: str
    original_filename: str
    mime_type: str
    type: AttachmentType
    size_bytes: int = Field(ge=0)
    status: AttachmentStatus
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    error_message: str | None = None
    transcription: str | None = None


class DraftStatus(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY = "READY"


class DraftFieldStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class DraftReviewAction(StrEnum):
    CONFIRM = "confirm"
    CORRECT = "correct"
    REJECT = "reject"


class PdfSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["PDF"] = "PDF"
    attachment_id: str
    page: int = Field(ge=1)


class SpreadsheetSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["SPREADSHEET"] = "SPREADSHEET"
    attachment_id: str
    sheet: str
    cell: str


class UserSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["USER"] = "USER"
    note: str | None = None


FieldSource = Annotated[
    PdfSource | SpreadsheetSource | UserSource, Field(discriminator="type")
]


class FieldRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    previous_raw_value: Any = None
    previous_normalized_value: Any = None
    previous_status: DraftFieldStatus
    changed_at: datetime
    source: FieldSource


class DraftField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    raw_value: Any
    normalized_value: Any = None
    status: DraftFieldStatus
    required: bool = False
    source: FieldSource
    history: list[FieldRevision] = Field(default_factory=list)


class ArticleRequestDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    conversation_id: str
    source_attachment_ids: list[str]
    status: DraftStatus
    fields: list[DraftField]
    created_at: datetime
    updated_at: datetime
