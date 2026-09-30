from types import SimpleNamespace
import importlib

import pytest

from solvo_client_agent.clients import CatalogApiError
from solvo_client_agent.state import (
    CURRENT_SEARCH,
    LAST_ARTICLE_CODE,
    LAST_COMPARISON_CODES,
    LAST_SEARCH_CODES,
)
compare_module = importlib.import_module("solvo_client_agent.tools.compare_articles")
detail_module = importlib.import_module("solvo_client_agent.tools.get_article")
search_module = importlib.import_module("solvo_client_agent.tools.search_articles")


class FakeClient:
    def __init__(self):
        self.calls = []
        self.error = None

    async def search_articles(self, **kwargs):
        self.calls.append(("search", kwargs))
        if self.error:
            raise self.error
        return {"items": [{"codigo": "900001"}, {"codigo": "900004"}]}

    async def get_article(self, codigo):
        self.calls.append(("detail", codigo))
        if self.error:
            raise self.error
        return {"identificacion": {"codigo": codigo}}

    async def compare_articles(self, codes):
        self.calls.append(("compare", codes))
        if self.error:
            raise self.error
        return {"comparedCodes": codes, "fields": []}


@pytest.fixture
def context():
    return SimpleNamespace(state={})


@pytest.mark.asyncio
async def test_search_maps_arguments_and_updates_state(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(search_module, "get_catalog_api_client", lambda: fake)
    filters = [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"}]
    result = await search_module.search_articles(context, filters=filters, page_size=10)
    assert result["ok"] is True
    assert fake.calls == [("search", {"filters": filters, "sort": [], "page": 1, "page_size": 10})]
    assert context.state[CURRENT_SEARCH]["filters"] == filters
    assert context.state[LAST_SEARCH_CODES] == ["900001", "900004"]


@pytest.mark.asyncio
async def test_detail_and_compare_update_state(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(detail_module, "get_catalog_api_client", lambda: fake)
    monkeypatch.setattr(compare_module, "get_catalog_api_client", lambda: fake)
    assert (await detail_module.get_article(context, "900001"))["ok"] is True
    assert context.state[LAST_ARTICLE_CODE] == "900001"
    codes = ["900001", "900002"]
    assert (await compare_module.compare_articles(context, codes))["ok"] is True
    assert context.state[LAST_COMPARISON_CODES] == codes


@pytest.mark.asyncio
async def test_tool_returns_normalized_error_without_state_change(monkeypatch, context):
    fake = FakeClient()
    fake.error = CatalogApiError("ARTICLE_NOT_FOUND", "missing", False, "not_found", 404)
    monkeypatch.setattr(detail_module, "get_catalog_api_client", lambda: fake)
    result = await detail_module.get_article(context, "999999")
    assert result == {
        "ok": False,
        "error": {
            "code": "ARTICLE_NOT_FOUND",
            "message": "missing",
            "retryable": False,
            "category": "not_found",
        },
    }
    assert context.state == {}


@pytest.mark.asyncio
async def test_tools_reject_invalid_arguments_before_http(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(search_module, "get_catalog_api_client", lambda: fake)
    monkeypatch.setattr(detail_module, "get_catalog_api_client", lambda: fake)
    monkeypatch.setattr(compare_module, "get_catalog_api_client", lambda: fake)

    bad_search = await search_module.search_articles(context, page_size=51)
    bad_detail = await detail_module.get_article(context, " ")
    bad_compare = await compare_module.compare_articles(context, ["900001", "900001"])

    assert bad_search["error"]["code"] == "INVALID_TOOL_ARGUMENT"
    assert bad_detail["error"]["code"] == "INVALID_TOOL_ARGUMENT"
    assert bad_compare["error"]["code"] == "INVALID_TOOL_ARGUMENT"
    assert fake.calls == []
