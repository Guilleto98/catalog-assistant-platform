"""Deterministic mapping from a reviewed request draft to similarity criteria."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ..domain.models import ArticleRequestDraft, DraftFieldStatus


class UsedDraftField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    value: Any
    status: DraftFieldStatus
    destinations: list[str]


class IgnoredDraftField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    status: DraftFieldStatus
    reason: str
    value: Any = None


class DraftSimilarityMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)
    features: dict[str, Any] = Field(default_factory=dict)
    required: dict[str, Any] = Field(default_factory=dict)
    used_fields: list[UsedDraftField] = Field(default_factory=list)
    ignored_fields: list[IgnoredDraftField] = Field(default_factory=list)


class DraftSimilarityMapper:
    """Apply status, metadata and value rules without involving an LLM."""

    def map(
        self,
        draft: ArticleRequestDraft,
        metadata: list[dict[str, Any]],
        *,
        include_proposed: bool = False,
    ) -> DraftSimilarityMapping:
        by_path = {item.get("path"): item for item in metadata}
        result = DraftSimilarityMapping()
        active = {DraftFieldStatus.CONFIRMED, DraftFieldStatus.CORRECTED}
        for item in draft.fields:
            proposed = item.status == DraftFieldStatus.PROPOSED and include_proposed
            if item.status not in active and not proposed:
                result.ignored_fields.append(IgnoredDraftField(
                    field=item.field, status=item.status, value=item.normalized_value,
                    reason=f"status_{item.status.value.lower()}_not_active",
                ))
                continue
            meta = by_path.get(item.field)
            if meta is None:
                result.ignored_fields.append(IgnoredDraftField(
                    field=item.field, status=item.status, value=item.normalized_value,
                    reason="field_not_in_catalog_metadata",
                ))
                continue
            value = item.normalized_value
            if not self._valid_value(value, meta):
                result.ignored_fields.append(IgnoredDraftField(
                    field=item.field, status=item.status, value=item.normalized_value,
                    reason="value_no_longer_valid",
                ))
                continue
            destinations: list[str] = []
            if bool(meta.get("usedForSimilarity")):
                result.features[item.field] = value
                destinations.append("features")
            if item.required and not proposed and bool(meta.get("canBeRequired")):
                result.required[item.field] = value
                destinations.append("required")
            if destinations:
                result.used_fields.append(UsedDraftField(
                    field=item.field, value=value, status=item.status,
                    destinations=destinations,
                ))
            else:
                reason = "required_not_supported" if item.required and not proposed else "field_not_supported_for_similarity"
                result.ignored_fields.append(IgnoredDraftField(
                    field=item.field, status=item.status, value=item.normalized_value, reason=reason,
                ))
        return result

    @staticmethod
    def _valid_value(value: Any, metadata: dict[str, Any]) -> bool:
        if value is None:
            return False
        allowed = metadata.get("allowedValues")
        if allowed is not None and value not in allowed:
            return False
        expected = metadata.get("type")
        return (
            (expected == "string" and isinstance(value, str))
            or (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (expected == "boolean" and isinstance(value, bool))
            or (expected == "date" and isinstance(value, str))
        )
