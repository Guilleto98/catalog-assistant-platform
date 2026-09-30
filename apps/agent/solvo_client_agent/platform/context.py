"""Server-controlled invocation identity; never sourced from LLM arguments."""

from contextvars import ContextVar

catalog_identity: ContextVar[str | None] = ContextVar("catalog_identity", default=None)
intake_drafts: ContextVar[object | None] = ContextVar("intake_drafts", default=None)
