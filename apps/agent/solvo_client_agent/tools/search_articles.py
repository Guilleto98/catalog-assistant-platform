"""Article search tool."""

from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..state import CURRENT_SEARCH, LAST_SEARCH_CODES, SELECTED_ARTICLE_CODES
from ._result import failure, invalid, success


ALLOWED_OPERATORS = {"eq", "neq", "in", "contains", "gte", "lte", "between", "is_null"}


async def search_articles(
    tool_context: ToolContext,
    filters: list[dict[str, Any]] | None = None,
    sort: list[dict[str, Any]] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search the catalog using structured filters, sorting and pagination.

    Use for characteristics such as cut, market, destination or temperature. For a
    conversational refinement, send the complete final search: keep unaffected
    filters from current_search, replace a filter on the same field, and reset page
    to 1 when filters change. Do not use for a known article code, comparison, or
    similarity. Filters contain only field, operator and value; never send SQL,
    expressions, URLs or code. Operators are eq, neq, in, contains, gte, lte,
    between and is_null. page_size must be between 1 and 50.

    Always use the Catalog API's exact field paths, never translated or shortened
    names. Common fields are producto_destino.corte, producto_destino.mercado,
    producto_destino.pais_destino, producto_destino.temperatura,
    identificacion.nombre and identificacion.codigo. Catalog enum values are
    uppercase, for example BIFE_ANCHO, CHINA, BRASIL, CONGELADO and REFRIGERADO.
    Example: bife ancho for China means two eq filters: field
    producto_destino.corte with value BIFE_ANCHO, and field
    producto_destino.mercado with value CHINA.
    """
    request = {
        "filters": filters or [],
        "sort": sort or [],
        "page": page,
        "page_size": page_size,
    }
    if not isinstance(page, int) or page < 1:
        return invalid("page debe ser un entero mayor o igual a 1.")
    if not isinstance(page_size, int) or not 1 <= page_size <= 50:
        return invalid("page_size debe ser un entero entre 1 y 50.")
    if not isinstance(request["filters"], list) or not isinstance(request["sort"], list):
        return invalid("filters y sort deben ser listas.")
    for item in request["filters"]:
        if not isinstance(item, dict) or set(item) - {"field", "operator", "value"}:
            return invalid("Cada filtro sólo puede contener field, operator y value.")
        if not isinstance(item.get("field"), str) or item.get("operator") not in ALLOWED_OPERATORS:
            return invalid("Cada filtro requiere field y un operator permitido.")
    for item in request["sort"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"field", "direction"}
            or not isinstance(item.get("field"), str)
            or item.get("direction") not in {"asc", "desc"}
        ):
            return invalid("Cada sort requiere field y direction asc o desc.")
    try:
        data = await get_catalog_api_client().search_articles(**request)
    except CatalogApiError as error:
        return failure(error)
    items = data.get("items", [])
    codes = [str(item["codigo"]) for item in items if item.get("codigo")]
    tool_context.state[CURRENT_SEARCH] = request
    tool_context.state[LAST_SEARCH_CODES] = codes
    tool_context.state[SELECTED_ARTICLE_CODES] = []
    return success(data)
