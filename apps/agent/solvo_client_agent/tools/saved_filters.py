"""User-owned saved-filter tools. User identity never enters the model schema."""

from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..state import CURRENT_SEARCH, LAST_SAVED_FILTER, LAST_SEARCH_CODES
from ._result import failure, invalid, success


def _user_id(tool_context: ToolContext) -> str | None:
    from ..platform.context import catalog_identity
    mapped = catalog_identity.get()
    application_id = getattr(tool_context, "user_id", "")
    if isinstance(application_id, str) and application_id.startswith("app:"):
        return mapped
    if mapped is not None:
        return mapped
    value = getattr(tool_context, "user_id", None)
    return value if isinstance(value, str) and value else None


async def save_filter(
    tool_context: ToolContext,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Save the exact current search criteria under a user-provided name.

    Requires current_search in session state. Never reconstruct filters from prose
    and never ask the model for a user identifier.
    """
    search = tool_context.state.get(CURRENT_SEARCH)
    user_id = _user_id(tool_context)
    if not isinstance(search, dict):
        return invalid("Primero realizá una búsqueda para poder guardar sus criterios exactos.")
    if not isinstance(name, str) or not name.strip():
        return invalid("name debe ser un texto no vacío.")
    if user_id is None:
        return invalid("La sesión no tiene un usuario asociado.")
    try:
        data = await get_catalog_api_client().save_filter(
            user_id=user_id, name=name.strip(), description=description, search=search
        )
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_SAVED_FILTER] = {"id": data.get("id"), "name": data.get("name")}
    return success(data)


async def list_saved_filters(tool_context: ToolContext) -> dict[str, Any]:
    """List filters owned by the current session user for display or name resolution."""
    user_id = _user_id(tool_context)
    if user_id is None:
        return invalid("La sesión no tiene un usuario asociado.")
    try:
        data = await get_catalog_api_client().list_saved_filters(user_id=user_id)
    except CatalogApiError as error:
        return failure(error)
    return success({"items": data})


async def get_saved_filter(tool_context: ToolContext, filter_id: str) -> dict[str, Any]:
    """Get one current-user saved filter by its exact identifier."""
    user_id = _user_id(tool_context)
    if user_id is None or not isinstance(filter_id, str) or not filter_id.strip():
        return invalid("Se necesita una sesión con usuario y un filter_id válido.")
    try:
        data = await get_catalog_api_client().get_saved_filter(filter_id.strip(), user_id=user_id)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_SAVED_FILTER] = {"id": data.get("id"), "name": data.get("name")}
    return success(data)


async def execute_saved_filter(tool_context: ToolContext, filter_id: str) -> dict[str, Any]:
    """Execute one current-user saved filter by exact identifier.

    Resolve a name first with list_saved_filters and proceed only if unique.
    """
    user_id = _user_id(tool_context)
    if user_id is None or not isinstance(filter_id, str) or not filter_id.strip():
        return invalid("Se necesita una sesión con usuario y un filter_id válido.")
    try:
        saved = await get_catalog_api_client().get_saved_filter(filter_id.strip(), user_id=user_id)
        data = await get_catalog_api_client().execute_saved_filter(filter_id.strip(), user_id=user_id)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[CURRENT_SEARCH] = saved.get("search", {})
    tool_context.state[LAST_SEARCH_CODES] = [
        str(item["codigo"]) for item in data.get("items", []) if item.get("codigo")
    ]
    tool_context.state[LAST_SAVED_FILTER] = {"id": saved.get("id"), "name": saved.get("name")}
    return success(data)


async def delete_saved_filter(tool_context: ToolContext, filter_id: str) -> dict[str, Any]:
    """Delete one current-user saved filter by exact identifier.

    This removes only the saved query and never mutates catalog articles.
    Resolve names with list_saved_filters; ask if more than one match exists.
    """
    user_id = _user_id(tool_context)
    if user_id is None or not isinstance(filter_id, str) or not filter_id.strip():
        return invalid("Se necesita una sesión con usuario y un filter_id válido.")
    try:
        saved = await get_catalog_api_client().get_saved_filter(filter_id.strip(), user_id=user_id)
        await get_catalog_api_client().delete_saved_filter(filter_id.strip(), user_id=user_id)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_SAVED_FILTER] = {"id": filter_id.strip(), "deleted": True}
    return success({"id": filter_id.strip(), "name": saved["name"], "deleted": True})
