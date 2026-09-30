"""Deterministic creation and human review of article request drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..domain.errors import IntakeError
from ..domain.models import (
    ArticleRequestDraft,
    DraftField,
    DraftFieldStatus,
    DraftReviewAction,
    DraftStatus,
    FieldRevision,
    UserSource,
)
from ..repositories import DraftRepository


FINAL_FIELD_STATUSES = {
    DraftFieldStatus.CONFIRMED,
    DraftFieldStatus.CORRECTED,
    DraftFieldStatus.REJECTED,
}


class DraftService:
    def __init__(self, repository: DraftRepository) -> None:
        self.repository = repository

    def create(
        self,
        conversation_id: str,
        attachment_ids: list[str],
        fields: list[DraftField],
    ) -> ArticleRequestDraft:
        now = datetime.now(timezone.utc)
        draft = ArticleRequestDraft(
            id=f"draft_{uuid4().hex}",
            conversation_id=conversation_id,
            source_attachment_ids=attachment_ids,
            status=DraftStatus.NEEDS_REVIEW,
            fields=fields,
            created_at=now,
            updated_at=now,
        )
        return self.repository.save(draft)

    def get(self, draft_id: str, conversation_id: str) -> ArticleRequestDraft:
        return self.repository.get(draft_id, conversation_id)

    def review_field(
        self,
        draft_id: str,
        conversation_id: str,
        field_path: str,
        action: str,
        normalized_value: Any = None,
        required: bool | None = None,
        note: str | None = None,
        field_metadata: dict[str, Any] | None = None,
    ) -> ArticleRequestDraft:
        draft = self.get(draft_id, conversation_id)
        index = next(
            (i for i, item in enumerate(draft.fields) if item.field == field_path),
            None,
        )
        if index is None:
            raise IntakeError("DRAFT_FIELD_NOT_FOUND", "El campo no existe en el borrador.", 404)
        current = draft.fields[index]
        action_status = {
            DraftReviewAction.CONFIRM: DraftFieldStatus.CONFIRMED,
            DraftReviewAction.CORRECT: DraftFieldStatus.CORRECTED,
            DraftReviewAction.REJECT: DraftFieldStatus.REJECTED,
        }.get(action)
        if action_status is None:
            raise IntakeError("INVALID_REVIEW_ACTION", "La acción de revisión no es válida.")
        if action == DraftReviewAction.CORRECT and normalized_value is None:
            raise IntakeError(
                "CORRECTION_VALUE_REQUIRED", "La corrección necesita un nuevo valor."
            )
        if action == DraftReviewAction.CORRECT and field_metadata is not None:
            allowed = field_metadata.get("allowedValues") or field_metadata.get(
                "allowed_values"
            )
            if allowed is not None and normalized_value not in allowed:
                raise IntakeError(
                    "INVALID_DRAFT_FIELD_VALUE",
                    "El valor corregido no pertenece al catálogo permitido.",
                    422,
                )
            expected = field_metadata.get("type")
            valid_type = (
                (expected == "string" and isinstance(normalized_value, str))
                or (
                    expected == "number"
                    and isinstance(normalized_value, (int, float))
                    and not isinstance(normalized_value, bool)
                )
                or (expected == "boolean" and isinstance(normalized_value, bool))
                or (expected == "date" and isinstance(normalized_value, str))
            )
            if not valid_type:
                raise IntakeError(
                    "INVALID_DRAFT_FIELD_TYPE",
                    "El valor corregido no tiene el tipo esperado.",
                    422,
                )
        now = datetime.now(timezone.utc)
        user_source = UserSource(note=note)
        revision = FieldRevision(
            previous_raw_value=current.raw_value,
            previous_normalized_value=current.normalized_value,
            previous_status=current.status,
            changed_at=now,
            source=user_source,
        )
        updated = current.model_copy(
            update={
                "normalized_value": (
                    normalized_value if action == "correct" else current.normalized_value
                ),
                "status": action_status,
                "required": current.required if required is None else required,
                "source": user_source if action == "correct" else current.source,
                "history": [*current.history, revision],
            }
        )
        new_fields = list(draft.fields)
        new_fields[index] = updated
        draft_status = (
            DraftStatus.READY
            if new_fields and all(item.status in FINAL_FIELD_STATUSES for item in new_fields)
            else DraftStatus.NEEDS_REVIEW
        )
        changed = draft.model_copy(
            update={"fields": new_fields, "status": draft_status, "updated_at": now}
        )
        return self.repository.save(changed)
