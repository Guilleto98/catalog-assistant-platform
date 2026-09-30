"""Structured contracts for semantic scope classification."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainScopeDecision(StrEnum):
    IN_SCOPE = "IN_SCOPE"
    ADJACENT_ALLOWED = "ADJACENT_ALLOWED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    AMBIGUOUS = "AMBIGUOUS"


class DomainScopeRequestKind(StrEnum):
    NORMAL = "NORMAL"
    MIXED = "MIXED"
    INTERNAL_CONFIGURATION = "INTERNAL_CONFIGURATION"


class DomainScopeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DomainScopeDecision
    reason: str = Field(min_length=1, max_length=300)
    request_kind: DomainScopeRequestKind = DomainScopeRequestKind.NORMAL


class DomainScopeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latest_message: str = Field(max_length=2000)
    recent_context: list[str] = Field(default_factory=list, max_length=4)
    state_summary: dict[str, str | bool | int | None] = Field(default_factory=dict)
