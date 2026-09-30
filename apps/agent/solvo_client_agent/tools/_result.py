"""Shared JSON-safe tool result helpers."""

from typing import Any

from ..clients import CatalogApiError


def success(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}


def failure(error: CatalogApiError) -> dict[str, Any]:
    return {"ok": False, "error": error.as_dict()}


def invalid(message: str) -> dict[str, Any]:
    return failure(
        CatalogApiError(
            code="INVALID_TOOL_ARGUMENT",
            message=message,
            retryable=False,
            category="validation",
        )
    )
