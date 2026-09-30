"""Metadata-only technical-sheet lookup."""

from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..state import LAST_ARTICLE_CODE, LAST_TECHNICAL_SHEET
from ._result import failure, invalid, success


async def get_technical_sheet(
    tool_context: ToolContext,
    codigo: str | None = None,
    ficha_id: str | None = None,
) -> dict[str, Any]:
    """Get technical-sheet metadata by article code or sheet identifier.

    Provide only one identifier. If omitted, the last selected article is used.
    The response is metadata only; never claim it contains a PDF or document body.
    """
    if codigo and ficha_id:
        return invalid("Indicá codigo o ficha_id, no ambos.")
    if not codigo and not ficha_id:
        codigo = tool_context.state.get(LAST_ARTICLE_CODE)
    if not codigo and not ficha_id:
        return invalid("No hay un artículo o ficha técnica inequívoca en el contexto.")
    try:
        data = await get_catalog_api_client().get_technical_sheet(codigo=codigo, ficha_id=ficha_id)
    except CatalogApiError as error:
        return failure(error)
    tool_context.state[LAST_TECHNICAL_SHEET] = {
        "ficha_id": data.get("fichaId"),
        "articulo_codigo": data.get("articuloCodigo"),
    }
    return success(data)
