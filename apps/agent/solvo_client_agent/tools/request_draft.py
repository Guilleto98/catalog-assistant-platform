"""Conversational human review of an existing intake draft."""

from functools import lru_cache
from typing import Any

from google.adk.tools import ToolContext

from ..config import get_settings
from ..clients import CatalogApiError, get_catalog_api_client
from ..domain.errors import IntakeError
from ..repositories import DraftRepository
from ..services import DraftService
from ..state.keys import CONVERSATION_ID, CURRENT_REQUEST_DRAFT_ID
from ._result import invalid, success


@lru_cache
def _draft_service() -> DraftService:
    return DraftService(DraftRepository(get_settings().intake_database_path))


def _context(tool_context: ToolContext) -> tuple[str, str] | None:
    conversation_id = tool_context.state.get(CONVERSATION_ID)
    draft_id = tool_context.state.get(CURRENT_REQUEST_DRAFT_ID)
    if not isinstance(conversation_id, str) or not isinstance(draft_id, str):
        return None
    return conversation_id, draft_id


async def get_request_draft(tool_context: ToolContext) -> dict[str, Any]:
    """Get the current article-request draft for review.

    Use only when current_request_draft_id and conversation_id already exist in
    session state. Never accept or guess a draft identifier from user text.
    """
    context = _context(tool_context)
    if context is None:
        return invalid("No hay un borrador asociado a esta conversación.")
    try:
        from ..platform.context import intake_drafts
        service = intake_drafts.get() or _draft_service()
        draft = service.get(context[1], context[0])
    except IntakeError as error:
        return {"ok": False, "error": {"code": error.code, "message": error.message}}
    return success(draft.model_dump(mode="json"))


async def review_request_draft(
    tool_context: ToolContext,
    field: str,
    action: str,
    normalized_value: str | float | int | bool | None = None,
    required: bool | None = None,
) -> dict[str, Any]:
    """Confirm, correct or reject one field of the current request draft.

    action must be confirm, correct or reject. For correct, pass the explicit
    normalized value stated by the user. Use only an exact field path already
    present in the current draft. This edits the request, never the catalog.
    """
    context = _context(tool_context)
    if context is None:
        return invalid("No hay un borrador asociado a esta conversación.")
    try:
        field_metadata = None
        if action == "correct":
            metadata = await get_catalog_api_client().get_filterable_fields()
            field_metadata = next(
                (item for item in metadata if item.get("path") == field), None
            )
            if field_metadata is None:
                return invalid("El campo no existe en los metadatos del catálogo.")
        from ..platform.context import intake_drafts
        service = intake_drafts.get() or _draft_service()
        draft = service.review_field(
            draft_id=context[1],
            conversation_id=context[0],
            field_path=field,
            action=action,
            normalized_value=normalized_value,
            required=required,
            note="Corrección realizada durante la conversación.",
            field_metadata=field_metadata,
        )
    except (IntakeError, CatalogApiError) as error:
        return {"ok": False, "error": {"code": error.code, "message": error.message}}
    return success(draft.model_dump(mode="json"))


async def update_request_draft(
    tool_context: ToolContext,
    field: str,
    action: str,
    normalized_value: str | float | int | bool | None = None,
    required: bool | None = None,
) -> dict[str, Any]:
    """Confirm, correct or reject one field of the current request draft.

    This is the public conversational update operation. It changes only the
    current request draft, never a catalog article. action is confirm, correct or
    reject; correct requires the explicit value supplied by the user.
    """
    return await review_request_draft(
        tool_context,
        field=field,
        action=action,
        normalized_value=normalized_value,
        required=required,
    )
