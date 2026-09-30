import httpx
import pytest

from solvo_client_agent.clients import CatalogApiClient, CatalogApiError


def client(handler):
    return CatalogApiClient(
        "http://catalog.test/api/v1", transport=httpx.MockTransport(handler)
    )


@pytest.mark.asyncio
async def test_search_maps_request_and_normalizes_response():
    async def handler(request):
        assert request.url.path == "/api/v1/articles/search"
        assert request.method == "POST"
        assert request.read()
        import json

        assert json.loads(request.content) == {
            "filters": [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"}],
            "sort": [],
            "page": 1,
            "page_size": 20,
        }
        return httpx.Response(201, json={"items": [{"codigo": "900001"}], "applied_filters": []})

    result = await client(handler).search_articles(
        [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"}]
    )
    assert result == {"items": [{"codigo": "900001"}], "appliedFilters": []}


@pytest.mark.asyncio
async def test_detail_uses_escaped_path():
    async def handler(request):
        assert request.url.path == "/api/v1/articles/900001"
        return httpx.Response(200, json={"ficha_id": "FT-DEMO-900001"})

    assert await client(handler).get_article("900001") == {"fichaId": "FT-DEMO-900001"}


@pytest.mark.asyncio
async def test_compare_maps_codes_and_normalizes_response():
    async def handler(request):
        import json

        assert json.loads(request.content) == {"codes": ["900001", "900002"]}
        return httpx.Response(201, json={"compared_codes": ["900001", "900002"]})

    result = await client(handler).compare_articles(["900001", "900002"])
    assert result["comparedCodes"] == ["900001", "900002"]


@pytest.mark.asyncio
async def test_reads_filterable_field_metadata():
    async def handler(request):
        assert request.url.path == "/api/v1/metadata/filterable-fields"
        return httpx.Response(
            200,
            json={"fields": [{"path": "producto_destino.mercado", "allowed_values": ["BRASIL"]}]},
        )

    fields = await client(handler).get_filterable_fields()
    assert fields == [
        {"path": "producto_destino.mercado", "allowedValues": ["BRASIL"]}
    ]


@pytest.mark.asyncio
async def test_similarity_and_technical_sheet_contracts():
    async def handler(request):
        import json

        if request.url.path.endswith("/articles/similar"):
            assert json.loads(request.content) == {
                "reference_code": "900001",
                "required": {"producto_destino.mercado": "CHINA"},
                "limit": 3,
            }
            return httpx.Response(201, json={"eligible_candidates": [], "ineligible_candidates": []})
        assert request.url.path.endswith("/articles/900001/technical-sheet")
        return httpx.Response(200, json={"ficha_id": "FT-DEMO-900001"})

    api = client(handler)
    similar = await api.find_similar_articles(
        reference_code="900001",
        required={"producto_destino.mercado": "CHINA"},
        limit=3,
    )
    assert similar["eligibleCandidates"] == []
    sheet = await api.get_technical_sheet(codigo="900001")
    assert sheet["fichaId"] == "FT-DEMO-900001"


@pytest.mark.asyncio
async def test_saved_filter_injects_owner_header_and_handles_list_and_delete():
    calls = []

    async def handler(request):
        calls.append((request.method, request.url.path, request.headers.get("x-demo-user-id")))
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(204)

    api = client(handler)
    assert await api.list_saved_filters(user_id="demo-user-01") == []
    await api.delete_saved_filter("filter-1", user_id="demo-user-01")
    assert calls == [
        ("GET", "/api/v1/saved-filters", "demo-user-01"),
        ("DELETE", "/api/v1/saved-filters/filter-1", "demo-user-01"),
    ]


@pytest.mark.asyncio
async def test_maps_validation_and_not_found_errors():
    async def validation(_request):
        return httpx.Response(400, json={"error": {"code": "INVALID_FILTER_VALUE", "message": "bad"}})

    with pytest.raises(CatalogApiError) as caught:
        await client(validation).search_articles()
    assert caught.value.category == "validation"
    assert caught.value.retryable is False

    async def missing(_request):
        return httpx.Response(404, json={"error": {"code": "ARTICLE_NOT_FOUND", "message": "missing"}})

    with pytest.raises(CatalogApiError) as caught:
        await client(missing).get_article("999999")
    assert caught.value.category == "not_found"


@pytest.mark.asyncio
async def test_maps_timeout_and_unavailable():
    async def timeout(request):
        raise httpx.ReadTimeout("late", request=request)

    with pytest.raises(CatalogApiError) as caught:
        await client(timeout).search_articles()
    assert caught.value.code == "CATALOG_API_TIMEOUT"
    assert caught.value.retryable is True

    async def unavailable(request):
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(CatalogApiError) as caught:
        await client(unavailable).get_article("900001")
    assert caught.value.code == "CATALOG_API_UNAVAILABLE"
