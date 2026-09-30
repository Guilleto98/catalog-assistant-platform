"""Article comparison tool."""

from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..state import LAST_COMPARISON_CODES, SELECTED_ARTICLE_CODES
from ._result import failure, invalid, success


async def compare_articles(
    tool_context: ToolContext, codes: list[str]
) -> dict[str, Any]:
    """Compare structured fields of two to ten unique known article codes.

    Use when the user wants differences between specific articles. Prefer this one
    call over retrieving every article separately. Do not use it to search for
    alternatives, and never calculate or invent comparison data locally.
    """
    if (
        not isinstance(codes, list)
        or not 2 <= len(codes) <= 10
        or any(not isinstance(code, str) or not code.strip() for code in codes)
        or len(set(codes)) != len(codes)
    ):
        return invalid("codes debe contener entre 2 y 10 códigos únicos no vacíos.")
    try:
        data = await get_catalog_api_client().compare_articles(codes)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_COMPARISON_CODES] = codes
    tool_context.state[SELECTED_ARTICLE_CODES] = codes
    return success(data)
