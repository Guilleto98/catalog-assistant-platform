"""Article detail tool."""

from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..state import LAST_ARTICLE_CODE, SELECTED_ARTICLE_CODES
from ._result import failure, invalid, success


async def get_article(tool_context: ToolContext, codigo: str) -> dict[str, Any]:
    """Retrieve complete structured details for one known article code.

    Use when the user gives a specific code or an unambiguous reference resolves to
    a code, including first/second/third from last_search_codes. Do not use this to
    search the catalog or compare multiple articles. Ask for clarification when the
    reference cannot be resolved reliably.
    """
    if not isinstance(codigo, str) or not codigo.strip():
        return invalid("codigo debe ser un string no vacío.")
    codigo = codigo.strip()
    try:
        data = await get_catalog_api_client().get_article(codigo)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_ARTICLE_CODE] = codigo
    tool_context.state[SELECTED_ARTICLE_CODES] = [codigo]
    return success(data)
