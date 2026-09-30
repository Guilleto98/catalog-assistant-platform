"""V1 projections, persistence, independent history and typed OpenAPI acceptance."""
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from uuid import uuid4

import httpx
import pytest
from google.adk import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from solvo_client_agent.api.app import create_app
from solvo_client_agent.clients.catalog_api import _camelize
from solvo_client_agent.platform import contracts as c, presenters as p
from solvo_client_agent.platform.models import AgentRun, Conversation, Message, ToolExecution, UiEvent
from solvo_client_agent.platform.runtime import AgentRuntime
from solvo_client_agent.services import DocumentExtractionService
from solvo_client_agent.services.extraction import ExtractionCandidate
from solvo_client_agent.tools import (search_articles, get_article, compare_articles, find_similar_articles, get_technical_sheet,
    save_filter, list_saved_filters, get_saved_filter, execute_saved_filter, delete_saved_filter)
from scripts.contract_samples import ROOT, examples, article, search_result, compare_result, similar_result, sheet_result, draft_result, filter_result
from test_platform import bootstrap, login, send, config, fake_scope
from test_intake import xlsx_bytes, FakeCatalog, FakeExtractor


@pytest.mark.parametrize("name", list(examples()))
def test_documentation_examples_match_real_models(name):
    model = examples()[name]
    path = ROOT / "docs/contracts/examples" / f"{name}.json"
    type(model).model_validate(json.loads(path.read_text()))
    assert json.loads(path.read_text()) == model.model_dump(mode="json")


def test_article_projection_does_not_invent_or_leak():
    source = article()
    source["adkSessionId"] = "PRIVATE"
    source["metadata"] = {"secret": "PRIVATE"}
    projected = p.article_list(_camelize(source))
    assert projected.code == "900001" and projected.active is True
    assert projected.anatomicalGroup == "DORSAL"
    assert projected.primaryPackaging == "VACIO"
    detail = p.article_detail(_camelize(source)).model_dump_json()
    assert "PRIVATE" not in detail and "identification" in detail
    sparse = p.article_list({"codigo": "900001"})
    assert sparse.name is None and sparse.active is None


def test_comparison_status_is_copied_not_recomputed():
    result = compare_result()
    result["fields"][0]["different"] = False
    value = p.comparison(result)
    assert value.rows[0].status == "SAME"  # transport doesn't overrule Catalog
    assert [v.articleCode for v in value.rows[0].values] == ["900001", "900002"]


def test_similarity_critical_eligibility_and_empty_lists():
    result = similar_result()
    dto = p.similarity(result, {"reference_code": "900001"}, {})
    assert (dto.ineligibleCandidates[0].article.code, dto.ineligibleCandidates[0].score, dto.ineligibleCandidates[0].eligibility) == ("900004", 90, "INELIGIBLE")
    assert (dto.eligibleCandidates[0].article.code, dto.eligibleCandidates[0].score, dto.eligibleCandidates[0].eligibility) == ("900006", 70, "ELIGIBLE")
    assert any(v.required and v.status == "MISMATCH" for v in dto.ineligibleCandidates[0].criteria)
    assert dto.usedCriteria[0].field == "identificacion.especie"
    result["result"]["eligibleCandidates"] = []
    assert p.similarity(result, {"reference_code": "900001"}, {}).eligibleCandidates == []
    result["result"]["ineligibleCandidates"][0]["requiredEvaluation"][0].update(candidateValue=None, status="NOT_AVAILABLE")
    assert p.similarity(result, {"reference_code": "900001"}, {}).ineligibleCandidates[0].criteria[-1].status == "NOT_AVAILABLE"


@pytest.mark.parametrize("reason,expected", [("field_not_supported_for_similarity", "NOT_SUPPORTED_FOR_SIMILARITY"),
    ("status_proposed_not_active", "UNCONFIRMED"), ("status_rejected_not_active", "REJECTED"),
    ("status_needs_clarification_not_active", "NEEDS_CLARIFICATION"), ("unknown", "OTHER")])
def test_ignored_criteria_keep_values_and_closed_reasons(reason, expected):
    result = similar_result()
    result["draftMapping"] = {"ignoredFields": [{"field": "producto_destino.mercado", "value": "CHINA", "reason": reason}]}
    dto = p.similarity(result, {"use_current_draft": True}, {"last_similarity": {"mode": "draft", "draft_id": "draft"}})
    assert dto.mode == "DRAFT" and dto.draftId == "draft"
    assert dto.ignoredCriteria[0].reason == expected and dto.ignoredCriteria[0].value == "CHINA"


@pytest.mark.parametrize("status", ["PROPOSED", "CONFIRMED", "CORRECTED", "REJECTED", "NEEDS_CLARIFICATION"])
def test_draft_preserves_status_and_safe_provenance(status):
    source = draft_result()
    source["fields"][0]["status"] = status
    dto = p.draft(source)
    assert dto.fields[0].status == status and dto.fields[0].source.cell == "B2"
    source["fields"][0]["source"] = {"type": "USER", "note": "INTERNAL"}
    assert "INTERNAL" not in p.draft(source).model_dump_json()


def test_saved_filters_noise_and_privacy():
    saved = p.saved_filter(filter_result())
    assert "DO_NOT_EXPOSE" not in saved.model_dump_json()
    listing = ("list_saved_filters", "SAVED_FILTER_LIST", c.SavedFilterListPayload(filters=[saved]))
    search = ("execute_saved_filter", "ARTICLE_SEARCH_RESULTS", examples()["article-search-results"])
    assert [e[0] for e in p.final_events([listing, search])] == ["ARTICLE_SEARCH_RESULTS"]
    assert [e[0] for e in p.final_events([listing])] == ["SAVED_FILTER_LIST"]
    assert p.present("get_filterable_fields", {"ok": True, "data": {}}, {}, {}) == []
    assert p.present("save_filter", {"ok": True, "data": filter_result()}, {}, {})[0][0] == "SAVED_FILTER_CREATED"
    assert p.present("delete_saved_filter", {"ok": True, "data": {"id": saved.id, "name": saved.name}}, {}, {})[0][1].name == saved.name


def test_domain_paths_survive_client_camelization():
    value = _camelize({"criteria_used": {"weighted": {"producto_destino.pais_destino": "CHINA"}}})
    assert value["criteriaUsed"]["weighted"] == {"producto_destino.pais_destino": "CHINA"}


class ScriptedModel(BaseLlm):
    async def generate_content_async(self, llm_request, stream=False):
        last = llm_request.contents[-1]
        if any(p.function_response for p in last.parts or []):
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Texto conversacional sin datos para parsear.")]))
            return
        text = " ".join(p.text or "" for p in last.parts).lower()
        name, args = "search_articles", {"filters": [{"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}]}
        if "primero" in text: name, args = "get_article", {"codigo": "900001"}
        if "compará" in text: name, args = "compare_articles", {"codes": ["900001", "900002"]}
        if "parecido" in text: name, args = "find_similar_articles", {"reference_code": "900001"}
        if "ficha" in text: name, args = "get_technical_sheet", {"codigo": "900001"}
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]))


class FakeFullCatalog:
    async def search_articles(self, **kwargs): return search_result()
    async def get_article(self, codigo): return _camelize(article(codigo))
    async def compare_articles(self, codes): return compare_result()
    async def find_similar_articles(self, **kwargs): return similar_result()["result"]
    async def get_technical_sheet(self, **kwargs): return sheet_result()


@asynccontextmanager
async def running(config):
    agent = Agent(name="contracts_test", model=ScriptedModel(model="test"), instruction="Catálogo.",
        tools=[search_articles, get_article, compare_articles, find_similar_articles, get_technical_sheet], before_model_callback=fake_scope)
    app = create_app(config, runtime=AgentRuntime(config.adk_database_path, agent))
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield app, client


@pytest.mark.asyncio
async def test_tool_to_ui_event_persist_restart_history_without_dependencies(config, monkeypatch):
    for module in ("search_articles", "get_article", "compare_articles", "similar_articles", "technical_sheet"):
        monkeypatch.setattr(importlib.import_module("solvo_client_agent.tools." + module), "get_catalog_api_client", lambda: FakeFullCatalog())
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client)
        cid = (await client.post("/api/v1/conversations")).json()["id"]
        for text, kind in [("Buscame bife ancho para China", "ARTICLE_SEARCH_RESULTS"), ("Mostrame el primero", "ARTICLE_DETAIL"),
            ("Compará 900001 con 900002", "ARTICLE_COMPARISON"), ("Algo parecido al 900001", "SIMILARITY_RESULTS"), ("Su ficha", "TECHNICAL_SHEET")]:
            mid = str(uuid4())
            body = {"clientMessageId": mid, "text": text, "attachmentIds": []}
            response = await client.post(f"/api/v1/conversations/{cid}/messages", json=body)
            assert response.status_code == 200, response.text
            dto = c.SendMessageResponse.model_validate(response.json())
            assert dto.assistantMessage.uiEvents[0].type == kind
            assert dto.assistantMessage.uiEvents[0].messageId == dto.assistantMessage.id
            assert dto.assistantMessage.uiEvents[0].sequence == 1
            assert (await client.post(f"/api/v1/conversations/{cid}/messages", json=body)).json() == response.json()
            for private in ("adk_session_id", "adkSessionId", "adkInvocationId", "scope_decision", "trace_id", "catalogDemoUserId", "password_hash"):
                assert private not in response.text
        before = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
        assert before["total"] == 10
        page1 = (await client.get(f"/api/v1/conversations/{cid}/messages?pageSize=2&page=1")).json()
        page2 = (await client.get(f"/api/v1/conversations/{cid}/messages?pageSize=2&page=2")).json()
        assert page1["items"] + page2["items"] == before["items"][:4]
        with app.state.platform.database.session() as db:
            assert len(db.scalars(select(AgentRun)).all()) == 5
            assert len(db.scalars(select(ToolExecution)).all()) == 5
        for operation in (update(UiEvent).values(payload_json={}), delete(UiEvent)):
            with pytest.raises(IntegrityError):
                with app.state.platform.database.session.begin() as db: db.execute(operation)
    async with running(config) as (app, client):
        def forbidden(*args, **kwargs): raise AssertionError("History must not execute dependencies")
        monkeypatch.setattr(app.state.platform.runtime, "execute", forbidden)
        monkeypatch.setattr(app.state.platform.runtime.sessions, "get_session", forbidden)
        monkeypatch.setattr(app.state.container.attachments, "get", forbidden)
        monkeypatch.setattr(importlib.import_module("solvo_client_agent.platform.presenters"), "present", forbidden)
        for module in ("search_articles", "get_article", "compare_articles", "similar_articles", "technical_sheet"):
            monkeypatch.setattr(importlib.import_module("solvo_client_agent.tools." + module), "get_catalog_api_client", forbidden)
        await login(client)
        assert (await client.get(f"/api/v1/conversations/{cid}/messages")).json() == before
        assert (await client.get(f"/api/v1/conversations/{cid}")).status_code == 200
        await login(client, "admin@example.test", "admin-password-123")
        admin = (await client.get(f"/api/v1/admin/conversations/{cid}")).json()
        assert admin["messages"] == before["items"] and len(admin["toolExecutions"]) == 5


@pytest.mark.asyncio
async def test_attachment_only_audio_transcript_and_draft_snapshots(config, monkeypatch):
    monkeypatch.setattr(importlib.import_module("solvo_client_agent.api.intake_service"), "get_catalog_api_client", lambda: FakeCatalog())
    monkeypatch.setattr(importlib.import_module("solvo_client_agent.tools.search_articles"), "get_catalog_api_client", lambda: FakeFullCatalog())
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client)
        cid = (await client.post("/api/v1/conversations")).json()["id"]
        assert (await send(client, cid, "  ")).json()["error"]["code"] == "INVALID_MESSAGE"
        upload = await client.post(f"/api/v1/conversations/{cid}/attachments", files={"file": ("pedido.xlsx", xlsx_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert upload.status_code == 201
        assert upload.json()["filename"] == "pedido.xlsx" and "storage" not in upload.text
        aid = upload.json()["id"]
        invalid_operation = await client.post(f"/api/v1/conversations/{cid}/attachments/{aid}/transcribe")
        assert invalid_operation.status_code == 422
        assert (await client.get(f"/api/v1/conversations/{cid}/attachments/{aid}")).json()["status"] == "UPLOADED"
        assert (await send(client, cid, None, attachments=[aid])).json()["error"]["code"] == "ATTACHMENT_NOT_READY"
        app.state.container.extraction = DocumentExtractionService(FakeExtractor([ExtractionCandidate(field="producto_destino.mercado",
            raw_value="China", normalized_value="CHINA", required=True, sheet="Solicitud", cell="B1")]))
        analyzed = await client.post(f"/api/v1/conversations/{cid}/attachments/{aid}/analyze")
        assert analyzed.status_code == 200, analyzed.text
        did = analyzed.json()["draft"]["draftId"]
        correction = await client.post(f"/api/v1/conversations/{cid}/drafts/{did}/review", json={"field": "producto_destino.mercado",
            "action": "correct", "normalized_value": "BRASIL"})
        assert correction.status_code == 200, correction.text
        assert correction.json()["fields"][0]["status"] == "CORRECTED"
        history = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
        drafts = [e for m in history["items"] for e in m["uiEvents"] if e["type"] == "REQUEST_DRAFT"]
        assert [d["payload"]["fields"][0]["normalizedValue"] for d in drafts] == ["CHINA", "BRASIL"]
        class Transcriber:
            async def transcribe(self, path): return "Buscame bife ancho para China."
        app.state.container.transcriber = Transcriber()
        audio = await client.post(f"/api/v1/conversations/{cid}/attachments", files={"file": ("pedido.wav", b"RIFF0000WAVE0000", "audio/wav")})
        aid = audio.json()["id"]
        transcribed = await client.post(f"/api/v1/conversations/{cid}/attachments/{aid}/transcribe")
        assert transcribed.json()["transcription"] == "Buscame bife ancho para China."
        sent = await send(client, cid, None, attachments=[aid])
        assert sent.status_code == 200, sent.text
        assert sent.json()["userMessage"]["messageType"] == "AUDIO"
        monkeypatch.setattr(app.state.container.attachments, "get", lambda *args: (_ for _ in ()).throw(AssertionError("No Intake lookup in V1 history")))
        assert (await client.get(f"/api/v1/conversations/{cid}/messages")).status_code == 200


def test_openapi_precise_v1_contracts():
    schema = create_app().openapi()
    assert "/api/v1/auth/me" in schema["paths"]
    assert "/auth/me" not in schema["paths"]
    for path, operations in schema["paths"].items():
        if not path.startswith("/api/v1/"): continue
        for method, operation in operations.items():
            assert operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ApiError")
            success = operation["responses"].get("200", operation["responses"].get("201"))
            assert "$ref" in success["content"]["application/json"]["schema"]
    ui = schema["components"]["schemas"]["MessageDto"]["properties"]["uiEvents"]["items"]
    assert ui["discriminator"]["propertyName"] == "type" and len(ui["oneOf"]) == 11
    assert schema["components"]["securitySchemes"]["CookieSession"] == {"type": "apiKey", "in": "cookie", "name": "solvo_session"}
    assert schema["paths"]["/api/v1/auth/me"]["get"]["security"] == [{"CookieSession": []}]


@pytest.mark.asyncio
async def test_v1_errors_current_user_timestamps_and_sidebar_order(config):
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        unauthenticated = await client.get("/api/v1/auth/me", headers={"X-Request-Id": "req_test"})
        assert unauthenticated.json() == {"error": {"code": "AUTH_REQUIRED", "message": "Se requiere iniciar sesión.", "requestId": "req_test"}}
        await login(client)
        profile = (await client.get("/api/v1/auth/me")).json()
        assert set(profile) == {"id", "email", "role", "organization"}
        assert set(profile["organization"]) == {"id", "name"}
        older = (await client.post("/api/v1/conversations")).json()
        newer = (await client.post("/api/v1/conversations")).json()
        assert older["createdAt"].endswith("Z") and older["lastMessageAt"] is None
        with app.state.platform.database.session.begin() as db:
            db.get(Conversation, older["id"]).last_message_at = db.get(Conversation, newer["id"]).created_at
            db.get(Conversation, older["id"]).last_message_at = db.get(Conversation, older["id"]).last_message_at.replace(year=2027)
        sidebar = (await client.get("/api/v1/conversations")).json()["items"]
        assert sidebar[0]["id"] == older["id"]
        error = await client.get("/api/v1/nonexistent")
        assert error.status_code == 404
        assert c.ApiError.model_validate(error.json()).error.requestId == error.headers["X-Request-Id"]
        cors = await client.get("/api/v1/auth/me", headers={"Origin": config.frontend_origin})
        assert cors.headers["Access-Control-Allow-Origin"] == config.frontend_origin
        assert cors.headers["Access-Control-Allow-Credentials"] == "true"
        await client.post(f"/api/v1/conversations/{older['id']}/archive")
        result = await client.post(f"/api/v1/conversations/{older['id']}/attachments", files={"file": ("pedido.xlsx", xlsx_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert result.json()["error"]["code"] == "CONVERSATION_ARCHIVED"


class FilterModel(BaseLlm):
    async def generate_content_async(self, llm_request, stream=False):
        last = llm_request.contents[-1]
        responses = [p.function_response for p in last.parts or [] if p.function_response]
        text = " ".join(p.text or "" for item in llm_request.contents if item.role == "user" for p in item.parts or []).lower()
        if responses:
            if responses[-1].name == "list_saved_filters" and "ejecutá" in text:
                name, args = "execute_saved_filter", {"filter_id": "filter_example"}
            else:
                yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Operación sobre filtro completada.")]))
                return
        elif "borrá" in text: name, args = "delete_saved_filter", {"filter_id": "filter_example"}
        elif "guardá" in text: name, args = "save_filter", {"name": "China"}
        else: name, args = "list_saved_filters", {}
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]))


@pytest.mark.asyncio
async def test_saved_filter_tools_persist_all_events_and_suppress_resolution_cards(config, monkeypatch):
    identities = []
    class Catalog:
        async def list_saved_filters(self, *, user_id):
            identities.append(user_id)
            return [filter_result()]
        async def get_saved_filter(self, filter_id, *, user_id):
            identities.append(user_id)
            return filter_result()
        async def execute_saved_filter(self, filter_id, *, user_id):
            identities.append(user_id)
            return search_result()
        async def save_filter(self, **kwargs):
            identities.append(kwargs["user_id"])
            return filter_result()
        async def delete_saved_filter(self, filter_id, *, user_id): identities.append(user_id)
    monkeypatch.setattr(importlib.import_module("solvo_client_agent.tools.saved_filters"), "get_catalog_api_client", lambda: Catalog())
    agent = Agent(name="filter_test", model=FilterModel(model="test"), instruction="Catálogo",
        tools=[save_filter, list_saved_filters, get_saved_filter, execute_saved_filter, delete_saved_filter])
    app = create_app(config, runtime=AgentRuntime(config.adk_database_path, agent))
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        bootstrap(app.state.platform)
        await login(client)
        for text, expected in [("Mis filtros", "SAVED_FILTER_LIST"), ("Ejecutá China", "ARTICLE_SEARCH_RESULTS"),
            ("Guardá esta búsqueda", "SAVED_FILTER_CREATED"), ("Borrá China", "SAVED_FILTER_DELETED")]:
            cid = (await client.post("/api/v1/conversations")).json()["id"]
            with app.state.platform.database.session() as db: conv = db.get(Conversation, cid)
            from google.adk.events import Event, EventActions
            session = await app.state.platform.runtime.sessions.get_session(app_name="solvo_client_product",
                user_id=f"app:{conv.owner_user_id}", session_id=conv.adk_session_id)
            await app.state.platform.runtime.sessions.append_event(session, Event(author="application", actions=EventActions(
                state_delta={"current_search": {"filters": [{"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}]}})))
            result = await send(client, cid, text)
            assert result.status_code == 200, result.text
            assert [e["type"] for e in result.json()["assistantMessage"]["uiEvents"]] == [expected]
            history = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()["items"]
            assert history[-1]["uiEvents"] == result.json()["assistantMessage"]["uiEvents"]
        assert identities and all(i == "demo-user-01" for i in identities)
