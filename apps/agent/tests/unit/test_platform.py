"""HTTP isolation and real persistent ADK runtime tests without paid model calls."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
import importlib
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from google.adk import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from solvo_client_agent.api.app import Container, create_app
from solvo_client_agent.platform.context import catalog_identity
from solvo_client_agent.platform.models import AgentRun, AuditEvent, AuthSession, Conversation, Message, Organization, User, now
from solvo_client_agent.platform.runtime import AgentRuntime, redact, result_summary
from solvo_client_agent.tools import search_articles, list_saved_filters
from test_intake import settings, pdf_bytes, xlsx_bytes, FakeExtractor, FakeCatalog
from solvo_client_agent.services import DocumentExtractionService
from solvo_client_agent.services.extraction import ExtractionCandidate


class DeterministicModel(BaseLlm):
    async def generate_content_async(self, llm_request, stream=False):
        last = llm_request.contents[-1]
        if any(p.function_response for p in last.parts or []):
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Resultado del catálogo.")]))
            return
        text = " ".join(p.text or "" for p in last.parts)
        if "fallo" in text:
            raise RuntimeError("sk-private-secret provider failed /private/path")
        if "filtros" in text:
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
                name="list_saved_filters", args={}))]))
            return
        current = []
        if "BIFE_ANCHO" in str(llm_request.config.system_instruction):
            current = [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"}]
        if "bife ancho" in text.lower():
            current = [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"}]
        if "China" in text:
            current.append({"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"})
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
            name="search_articles", args={"filters": current}))]))


async def fake_scope(callback_context, llm_request):
    text = " ".join(p.text or "" for p in callback_context.user_content.parts)
    decision = "OUT_OF_SCOPE" if "fútbol" in text else "IN_SCOPE"
    callback_context.state["domain_scope_decision"] = decision
    callback_context.state["domain_scope_reason"] = "Clasificación de prueba"
    callback_context.state["domain_scope_latency_ms"] = 1.0
    if decision == "OUT_OF_SCOPE":
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="Consultá sobre el catálogo.")]))


def agent():
    return Agent(name="test_catalog_agent", model=DeterministicModel(model="test"),
                 instruction="Búsqueda actual: {current_search?}", tools=[search_articles, list_saved_filters],
                 before_model_callback=fake_scope)


@pytest.fixture
def config(tmp_path):
    return replace(settings(tmp_path), legacy_intake_enabled=False,
                   application_database_path=tmp_path / "application.db", adk_database_path=tmp_path / "adk_sessions.db")


@pytest.fixture(autouse=True)
def catalog(monkeypatch):
    class Catalog:
        async def search_articles(self, **kwargs):
            return {"items": [{"codigo": "900001"}], "pagination": {"totalItems": 1}}
    module = importlib.import_module("solvo_client_agent.tools.search_articles")
    monkeypatch.setattr(module, "get_catalog_api_client", lambda: Catalog())


@asynccontextmanager
async def running(config):
    app = create_app(config, runtime=AgentRuntime(config.adk_database_path, agent()))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield app, client


def bootstrap(platform):
    auth = platform.auth
    org_a = auth.create_organization("Cliente A", "cliente-a")
    org_b = auth.create_organization("Cliente B", "cliente-b")
    a = auth.create_user("a@example.test", "test-password-123", "CLIENT_USER", org_a.id, "demo-user-01")
    b = auth.create_user("b@example.test", "test-password-456", "CLIENT_USER", org_b.id, "demo-user-02")
    admin = auth.create_user("admin@example.test", "admin-password-123", "INTERNAL_ADMIN")
    return a, b, admin


async def login(client, email="a@example.test", password="test-password-123"):
    return await client.post("/auth/login", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_saved_filter_read_contract_is_authenticated_and_user_scoped(config, monkeypatch):
    observed = []

    class Catalog:
        async def list_saved_filters(self, *, user_id):
            observed.append(user_id)
            return []

    service = importlib.import_module("solvo_client_agent.platform.service")
    monkeypatch.setattr(service, "get_catalog_api_client", lambda: Catalog())
    async with running(config) as (app, client):
        assert (await client.get("/saved-filters")).status_code == 401
        bootstrap(app.state.platform)
        assert (await login(client)).status_code == 200
        response = await client.get("/api/v1/saved-filters")
        assert response.status_code == 200
        assert response.json() == {"filters": []}
        assert observed == ["demo-user-01"]
        assert (await login(client, "b@example.test", "test-password-456")).status_code == 200
        assert (await client.get("/saved-filters")).json() == {"filters": []}
        assert observed == ["demo-user-01", "demo-user-02"]


async def send(client, cid, text, mid=None, attachments=None):
    return await client.post(f"/conversations/{cid}/messages", json={
        "clientMessageId": mid or str(uuid4()), "text": text, "attachmentIds": attachments or []})


@pytest.mark.asyncio
async def test_authentication_cookie_hash_logout_expiry_disabled(config):
    async with running(config) as (app, client):
        a, b, admin = bootstrap(app.state.platform)
        unknown = await login(client, "unknown@example.test")
        invalid = await login(client, password="incorrect")
        for response in (unknown, invalid):
            assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
            assert response.json()["error"]["message"] == "Credenciales inválidas."
            assert response.json()["error"]["requestId"] == response.headers["X-Request-Id"]
        result = await login(client)
        assert result.status_code == 200
        cookie = result.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
        with app.state.platform.database.session() as db:
            user = db.get(User, a.id)
            assert user.password_hash.startswith("$argon2id$")
            assert user.password_hash != "test-password-123"
            session = db.scalar(select(AuthSession))
            assert session.token_hash != client.cookies["solvo_session"]
        assert (await client.get("/auth/me")).status_code == 200
        raw = client.cookies["solvo_session"]
        await client.post("/auth/logout")
        client.cookies.set("solvo_session", raw)
        assert (await client.get("/auth/me")).status_code == 401
        client.cookies.clear()
        await login(client)
        with app.state.platform.database.session.begin() as db:
            for session in db.scalars(select(AuthSession)):
                session.expires_at = now() - timedelta(seconds=1)
        assert (await client.get("/auth/me")).json()["error"]["code"] == "SESSION_EXPIRED"
        await login(client)
        with app.state.platform.database.session.begin() as db:
            db.get(User, a.id).status = "DISABLED"
        assert (await client.get("/auth/me")).status_code == 403
        assert (await login(client)).status_code == 401


@pytest.mark.asyncio
async def test_restart_persists_context_idempotency_history_and_isolation(config):
    mid = str(uuid4())
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client)
        cid = (await client.post("/conversations")).json()["id"]
        first = await send(client, cid, "Buscame bife ancho.", mid)
        assert first.status_code == 200, first.text
        retry = await send(client, cid, "Buscame bife ancho.", mid)
        assert retry.json()["run"]["id"] == first.json()["run"]["id"]
        assert (await send(client, cid, "Otro mensaje", mid)).status_code == 409
        other = (await client.post("/conversations")).json()["id"]
        with app.state.platform.database.session() as db:
            assert len(db.scalars(select(AgentRun)).all()) == 1
            conv = db.get(Conversation, cid)
            assert conv.adk_session_id != cid
    async with running(config) as (app, client):
        await login(client)
        assert (await client.get(f"/conversations/{cid}/messages")).json()["total"] == 2
        result = await send(client, cid, "Solo los de China.")
        assert result.status_code == 200, result.text
        with app.state.platform.database.session() as db:
            conv = db.get(Conversation, cid)
        session = await app.state.platform.runtime.sessions.get_session(
            app_name="solvo_client_product", user_id=f"app:{conv.owner_user_id}", session_id=conv.adk_session_id)
        assert session.state["current_search"]["filters"] == [
            {"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"},
            {"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}]
        await send(client, other, "Solo los de China.")
        with app.state.platform.database.session() as db:
            conv = db.get(Conversation, other)
        session = await app.state.platform.runtime.sessions.get_session(
            app_name="solvo_client_product", user_id=f"app:{conv.owner_user_id}", session_id=conv.adk_session_id)
        assert session.state["current_search"]["filters"] == [
            {"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}]


@pytest.mark.asyncio
async def test_authorization_admin_audit_and_failures(config):
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client)
        cid = (await client.post("/conversations")).json()["id"]
        successful = await send(client, cid, "Buscame bife ancho para China.")
        assert successful.status_code == 200, successful.text
        failed = await send(client, cid, "Simular fallo")
        assert failed.status_code == 502
        assert "sk-private" not in failed.text
        scope = await send(client, cid, "Quiero fútbol")
        assert set(scope.json()["run"]) == {"id", "status", "error"}
        assert scope.json()["assistantMessage"]["uiEvents"] == []
        assert (await client.get("/admin/runs")).status_code == 403
        await login(client, "b@example.test", "test-password-456")
        assert (await client.get(f"/conversations/{cid}")).status_code == 404
        assert (await send(client, cid, "hola")).status_code == 404
        assert (await client.get("/conversations")).json()["total"] == 0
        await login(client, "admin@example.test", "admin-password-123")
        detail = await client.get(f"/admin/conversations/{cid}")
        assert detail.status_code == 200
        assert len(detail.json()["runs"]) == 3
        assert len(detail.json()["toolExecutions"]) == 1
        assert any(r["scope_decision"] == "OUT_OF_SCOPE" for r in detail.json()["runs"])
        run_detail = await client.get(f"/admin/runs/{successful.json()['run']['id']}")
        assert run_detail.json()["toolExecutions"][0]["status"] == "COMPLETED"
        events = (await client.get("/admin/audit-events", params={"conversationId": cid})).json()["items"]
        assert "ADMIN_CONVERSATION_VIEWED" in [e["event_type"] for e in events]
        assert "AGENT_RUN_FAILED" in [e["event_type"] for e in events]
        assert "password_hash" not in detail.text
        assert "sk-private" not in str(events)


@pytest.mark.asyncio
async def test_attachment_isolation_archive_and_request_headers(config):
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client)
        a = (await client.post("/conversations")).json()["id"]
        b = (await client.post("/conversations")).json()["id"]
        upload = await client.post(f"/conversations/{a}/attachments", files={"file": ("test.pdf", pdf_bytes("Pedido China"), "application/pdf")})
        assert upload.status_code == 201
        aid = upload.json()["id"]
        assert (await send(client, b, "Usá este archivo", attachments=[aid])).status_code == 403
        assert (await client.get(f"/conversations/{b}/attachments/{aid}")).status_code == 403
        assert (await client.post("/attachments", headers={"X-Demo-Conversation-Id": a})).status_code == 404
        response = await client.get("/conversations", params={"pageSize": 1}, headers={"X-Request-Id": "test-request"})
        assert response.headers["X-Request-Id"] == "test-request"
        assert response.json()["total"] == 2 and len(response.json()["items"]) == 1
        assert (await client.post(f"/conversations/{a}/archive")).json()["status"] == "ARCHIVED"
        assert (await send(client, a, "otro mensaje")).status_code == 409
        assert (await client.post("/conversations", headers={"Origin": "https://evil.test"})).status_code == 403


def test_redaction_and_document_summaries_exclude_private_data():
    assert redact({"authorization": "Bearer secret", "apiKey": "secret", "nested": {"value": "sk-test-secret"}}) == {
        "authorization": "[REDACTED]", "apiKey": "[REDACTED]", "nested": {"value": "[REDACTED]"}}
    summary = result_summary("get_request_draft", {"ok": True, "data": {"id": "draft", "fields": [{"raw_value": "private document"}], "status": "READY"}})
    assert "private document" not in str(summary)
    assert summary["fieldCount"] == 1


def test_saved_filter_identity_is_server_controlled():
    from solvo_client_agent.tools.saved_filters import _user_id
    context = SimpleNamespace(user_id="app:usr-123")
    assert _user_id(context) is None
    token = catalog_identity.set("demo-user-02")
    try:
        assert _user_id(context) == "demo-user-02"
    finally:
        catalog_identity.reset(token)


@pytest.mark.asyncio
async def test_private_reasoning_never_reaches_persistent_adk_events(config):
    from google.adk.events import Event
    runtime = AgentRuntime(config.adk_database_path, agent())
    sid = await runtime.create_session("test-user", "test-conversation")
    session = await runtime.sessions.get_session(app_name=runtime.app_name, user_id="app:test-user", session_id=sid)
    await runtime.sessions.append_event(session, Event(author="test_catalog_agent", content=types.Content(
        role="model", parts=[types.Part(text="private scratchpad", thought=True), types.Part(text="observable answer")]
    )))
    await runtime.close()
    runtime = AgentRuntime(config.adk_database_path, agent())
    session = await runtime.sessions.get_session(app_name=runtime.app_name, user_id="app:test-user", session_id=sid)
    assert "private scratchpad" not in session.model_dump_json()
    assert "observable answer" in session.model_dump_json()
    await runtime.close()


@pytest.mark.asyncio
async def test_secure_cookie_disabled_organization_and_append_only_audit(config):
    config = replace(config, auth_cookie_secure=True)
    async with running(config) as (app, client):
        a, b, admin = bootstrap(app.state.platform)
        result = await login(client)
        assert "secure" in result.headers["set-cookie"].lower()
        with app.state.platform.database.session.begin() as db:
            db.get(Organization, a.organization_id).status = "DISABLED"
        assert (await login(client)).status_code == 401
        for operation in [update(AuditEvent).values(event_type="ALTERED"), delete(AuditEvent)]:
            with pytest.raises(IntegrityError):
                with app.state.platform.database.session.begin() as db:
                    db.execute(operation)


@pytest.mark.asyncio
async def test_authenticated_saved_filters_use_database_identity(config, monkeypatch):
    identities = []
    class Filters:
        async def list_saved_filters(self, *, user_id):
            identities.append(user_id)
            return []
    monkeypatch.setattr(importlib.import_module("solvo_client_agent.tools.saved_filters"), "get_catalog_api_client", lambda: Filters())
    async with running(config) as (app, client):
        bootstrap(app.state.platform)
        await login(client, "b@example.test", "test-password-456")
        cid = (await client.post("/conversations")).json()["id"]
        result = await send(client, cid, "Listame mis filtros")
        assert result.status_code == 200, result.text
        assert identities == ["demo-user-02"]
        malicious = await client.post(f"/conversations/{cid}/messages", json={
            "clientMessageId": str(uuid4()), "text": "filtros", "catalogDemoUserId": "demo-user-01"})
        assert malicious.status_code == 422
        assert identities == ["demo-user-02"]


@pytest.mark.asyncio
async def test_authenticated_intake_sets_adk_draft_and_emits_audit(config, monkeypatch):
    monkeypatch.setattr(importlib.import_module("solvo_client_agent.api.intake_service"), "get_catalog_api_client", lambda: FakeCatalog())
    app = create_app(config, runtime=AgentRuntime(config.adk_database_path, agent()))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        bootstrap(app.state.platform)
        app.state.container.extraction = DocumentExtractionService(FakeExtractor([
            ExtractionCandidate(field="producto_destino.mercado", raw_value="Brasil", normalized_value="BRASIL",
                                required=True, sheet="Solicitud", cell="B1")]))
        await login(client)
        cid = (await client.post("/conversations")).json()["id"]
        uploaded = await client.post(f"/conversations/{cid}/attachments", files={"file": ("pedido.xlsx", xlsx_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        aid = uploaded.json()["id"]
        analyzed = await client.post(f"/conversations/{cid}/attachments/{aid}/analyze")
        assert analyzed.status_code == 200, analyzed.text
        draft_id = analyzed.json()["draft"]["draftId"]
        reviewed = await client.post(f"/conversations/{cid}/drafts/{draft_id}/review", json={
            "field": "producto_destino.mercado", "action": "confirm"})
        assert reviewed.status_code == 200
        with app.state.platform.database.session() as db:
            conversation = db.get(Conversation, cid)
            events = [v.event_type for v in db.scalars(select(AuditEvent).where(AuditEvent.conversation_id == cid))]
        assert all(e in events for e in ["ATTACHMENT_UPLOADED", "REQUEST_DRAFT_CREATED", "REQUEST_DRAFT_CONFIRMED"])
        session = await app.state.platform.runtime.sessions.get_session(app_name="solvo_client_product",
            user_id=f"app:{conversation.owner_user_id}", session_id=conversation.adk_session_id)
        assert session.state["current_request_draft_id"] == draft_id
