from types import SimpleNamespace
import importlib
from datetime import datetime, timezone

import pytest

from solvo_client_agent.state import (
    CONVERSATION_ID,
    CURRENT_SEARCH,
    CURRENT_REQUEST_DRAFT_ID,
    LAST_SAVED_FILTER,
    LAST_SEARCH_CODES,
    LAST_SIMILARITY,
    LAST_TECHNICAL_SHEET,
)
from solvo_client_agent.domain.models import (
    ArticleRequestDraft,
    DraftField,
    DraftFieldStatus,
    DraftStatus,
    UserSource,
)


similarity_module = importlib.import_module("solvo_client_agent.tools.similar_articles")
sheet_module = importlib.import_module("solvo_client_agent.tools.technical_sheet")
filters_module = importlib.import_module("solvo_client_agent.tools.saved_filters")


class FakeClient:
    def __init__(self):
        self.calls = []

    async def find_similar_articles(self, **kwargs):
        self.calls.append(("similar", kwargs))
        return {
            "criteriaUsed": {},
            "eligibleCandidates": [{"codigo": "900006", "eligibility": "ELIGIBLE"}],
            "ineligibleCandidates": [{"codigo": "900004", "eligibility": "INELIGIBLE"}],
        }

    async def get_technical_sheet(self, **kwargs):
        self.calls.append(("sheet", kwargs))
        return {"fichaId": "FT-DEMO-900006", "articuloCodigo": "900006"}

    async def save_filter(self, **kwargs):
        self.calls.append(("save", kwargs))
        return {"id": "f-1", "name": kwargs["name"], "search": kwargs["search"]}

    async def list_saved_filters(self, **kwargs):
        self.calls.append(("list", kwargs))
        return [{"id": "f-1", "name": "China"}]

    async def get_saved_filter(self, filter_id, **kwargs):
        self.calls.append(("get", filter_id, kwargs))
        return {
            "id": filter_id,
            "name": "China",
            "search": {"filters": [], "sort": [], "page": 1, "page_size": 20},
        }

    async def execute_saved_filter(self, filter_id, **kwargs):
        self.calls.append(("execute", filter_id, kwargs))
        return {"items": [{"codigo": "900001"}]}

    async def delete_saved_filter(self, filter_id, **kwargs):
        self.calls.append(("delete", filter_id, kwargs))


@pytest.fixture
def context():
    return SimpleNamespace(state={}, user_id="demo-user-01")


@pytest.mark.asyncio
async def test_similarity_keeps_eligible_and_ineligible_state(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(similarity_module, "get_catalog_api_client", lambda: fake)
    result = await similarity_module.find_similar_articles(
        context,
        reference_code="900001",
        required={"producto_destino.mercado": "CHINA"},
    )
    assert result["ok"] is True
    assert context.state[LAST_SIMILARITY] == {
        "mode": "reference",
        "draft_id": None,
        "reference_code": "900001",
        "eligible_codes": ["900006"],
        "ineligible_codes": ["900004"],
    }


@pytest.mark.asyncio
async def test_similarity_rejects_ambiguous_modes_without_http(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(similarity_module, "get_catalog_api_client", lambda: fake)
    result = await similarity_module.find_similar_articles(
        context, reference_code="900001", features={"identificacion.especie": "BOVINO"}
    )
    assert result["error"]["code"] == "INVALID_TOOL_ARGUMENT"
    assert fake.calls == []


@pytest.mark.asyncio
async def test_similarity_maps_only_current_conversation_draft(monkeypatch, context):
    fake = FakeClient()
    now = datetime.now(timezone.utc)
    current = ArticleRequestDraft(
        id="draft-1",
        conversation_id="conversation-1",
        source_attachment_ids=[],
        status=DraftStatus.READY,
        fields=[DraftField(
            field="producto_destino.mercado",
            raw_value="China",
            normalized_value="CHINA",
            status=DraftFieldStatus.CONFIRMED,
            required=True,
            source=UserSource(),
        )],
        created_at=now,
        updated_at=now,
    )

    class Drafts:
        def get(self, draft_id, conversation_id):
            assert (draft_id, conversation_id) == ("draft-1", "conversation-1")
            return current

    class Metadata:
        async def fields(self):
            return [{
                "path": "producto_destino.mercado",
                "type": "string",
                "allowedValues": ["CHINA"],
                "usedForSimilarity": True,
                "canBeRequired": True,
            }]

    monkeypatch.setattr(similarity_module, "get_catalog_api_client", lambda: fake)
    monkeypatch.setattr(similarity_module, "_draft_service", lambda: Drafts())
    monkeypatch.setattr(similarity_module, "_metadata_service", lambda: Metadata())
    context.state[CONVERSATION_ID] = "conversation-1"
    context.state[CURRENT_REQUEST_DRAFT_ID] = "draft-1"
    result = await similarity_module.find_similar_articles(context, use_current_draft=True)
    assert result["ok"] is True
    assert fake.calls[0][1]["features"] == {"producto_destino.mercado": "CHINA"}
    assert fake.calls[0][1]["required"] == {"producto_destino.mercado": "CHINA"}
    assert result["data"]["draftMapping"]["usedFields"][0]["destinations"] == [
        "features",
        "required",
    ]


@pytest.mark.asyncio
async def test_technical_sheet_is_metadata_only_and_updates_small_state(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(sheet_module, "get_catalog_api_client", lambda: fake)
    result = await sheet_module.get_technical_sheet(context, codigo="900006")
    assert result["data"]["fichaId"] == "FT-DEMO-900006"
    assert context.state[LAST_TECHNICAL_SHEET] == {
        "ficha_id": "FT-DEMO-900006",
        "articulo_codigo": "900006",
    }


@pytest.mark.asyncio
async def test_saved_filter_uses_exact_current_search_and_context_user(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(filters_module, "get_catalog_api_client", lambda: fake)
    search = {"filters": [{"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}], "sort": [], "page": 1, "page_size": 20}
    context.state[CURRENT_SEARCH] = search
    result = await filters_module.save_filter(context, "China")
    assert result["ok"] is True
    assert fake.calls[0] == (
        "save",
        {"user_id": "demo-user-01", "name": "China", "description": None, "search": search},
    )
    assert context.state[LAST_SAVED_FILTER] == {"id": "f-1", "name": "China"}


@pytest.mark.asyncio
async def test_execute_filter_restores_search_and_result_order(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(filters_module, "get_catalog_api_client", lambda: fake)
    result = await filters_module.execute_saved_filter(context, "f-1")
    assert result["ok"] is True
    assert context.state[CURRENT_SEARCH]["filters"] == []
    assert context.state[LAST_SEARCH_CODES] == ["900001"]
    assert all(call[-1].get("user_id") == "demo-user-01" for call in fake.calls)


@pytest.mark.asyncio
async def test_save_requires_a_current_search(monkeypatch, context):
    fake = FakeClient()
    monkeypatch.setattr(filters_module, "get_catalog_api_client", lambda: fake)
    result = await filters_module.save_filter(context, "Nada")
    assert result["error"]["code"] == "INVALID_TOOL_ARGUMENT"
    assert fake.calls == []
