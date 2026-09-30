"""One real-model V1 catalog + document flow; restart/read with HTTP blocked."""
import asyncio
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
import secrets
import time

import httpx
from openpyxl import Workbook
from solvo_client_agent.api.app import create_app
from solvo_client_agent.config import get_settings
from solvo_client_agent.platform import contracts as c

BASE = "/api/v1"


def document_bytes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Pedido"
    for row in [("Corte", "Bife ancho"), ("Mercado obligatorio", "China"), ("Temperatura obligatoria", "Congelado")]:
        sheet.append(row)
    target = BytesIO()
    workbook.save(target)
    return target.getvalue()


async def main():
    password = secrets.token_urlsafe(24)
    email = "platform-smoke@example.test"
    report = {"catalogFlow": [], "documentFlow": [], "historyWithoutDependencies": False}
    histories = {}
    with TemporaryDirectory(prefix="solvo-client-platform-smoke-") as temp:
        root = Path(temp)
        config = replace(get_settings(), application_database_path=root / "application.db",
            adk_database_path=root / "adk_sessions.db", intake_database_path=root / "intake.db",
            attachment_storage_path=root / "attachments", legacy_intake_enabled=False, auth_cookie_secure=False)
        app = create_app(config)
        async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://smoke") as client:
            org = app.state.platform.auth.create_organization("Smoke", "smoke")
            app.state.platform.auth.create_user(email, password, "CLIENT_USER", org.id, "demo-user-01")
            app.state.platform.auth.create_user("admin-smoke@example.test", password, "INTERNAL_ADMIN")
            assert (await client.post(BASE + "/auth/login", json={"email": email, "password": password})).status_code == 200
            cid = (await client.post(BASE + "/conversations")).json()["id"]
            async def message(conversation_id, text, expected, output):
                started = time.perf_counter()
                response = await client.post(f"{BASE}/conversations/{conversation_id}/messages", json={
                    "clientMessageId": str(uuid4()), "text": text, "attachmentIds": []})
                assert response.status_code == 200, response.text
                dto = c.SendMessageResponse.model_validate(response.json())
                kinds = [event.type for event in dto.assistantMessage.uiEvents]
                assert expected in kinds, (text, kinds, dto.assistantMessage.text)
                assert all(e.messageId == dto.assistantMessage.id for e in dto.assistantMessage.uiEvents)
                output.append({"input": text, "status": dto.run.status, "events": kinds,
                    "durationMs": round((time.perf_counter()-started)*1000, 1), "answer": dto.assistantMessage.text})
                return dto
            for text, expected in [("Buscame bife ancho para China.", "ARTICLE_SEARCH_RESULTS"),
                ("Mostrame el primero.", "ARTICLE_DETAIL"),
                ("Buscame algo parecido al 900001, pero China y congelado son obligatorios.", "SIMILARITY_RESULTS"),
                ("Mostrame la ficha del 900001.", "TECHNICAL_SHEET")]:
                dto = await message(cid, text, expected, report["catalogFlow"])
                if expected == "SIMILARITY_RESULTS":
                    result = next(e.payload for e in dto.assistantMessage.uiEvents if e.type == expected)
                    bad = next(v for v in result.ineligibleCandidates if v.article.code == "900004")
                    good = next(v for v in result.eligibleCandidates if v.article.code == "900006")
                    assert (bad.score, bad.eligibility, good.score, good.eligibility) == (90, "INELIGIBLE", 70, "ELIGIBLE")
            document_cid = (await client.post(BASE + "/conversations")).json()["id"]
            response = await client.post(f"{BASE}/conversations/{document_cid}/attachments", files={"file": (
                "pedido.xlsx", document_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert response.status_code == 201, response.text
            aid = c.AttachmentDto.model_validate(response.json()).id
            response = await client.post(f"{BASE}/conversations/{document_cid}/attachments/{aid}/analyze")
            assert response.status_code == 200, response.text
            draft = c.AnalyzeResponse.model_validate(response.json()).draft
            assert any(f.field == "producto_destino.mercado" for f in draft.fields)
            report["documentFlow"].append({"operation": "upload/analyze", "draftStatus": draft.status,
                "fields": [{"field": f.field, "status": f.status, "value": f.normalizedValue} for f in draft.fields]})
            await message(document_cid, "Corregí el mercado del borrador: no es China, es Brasil.", "REQUEST_DRAFT", report["documentFlow"])
            dto = await message(document_cid, "Buscame algo parecido usando el borrador actual con lo disponible, incluidos los campos propuestos.",
                "SIMILARITY_RESULTS", report["documentFlow"])
            similar = next(e.payload for e in dto.assistantMessage.uiEvents if e.type == "SIMILARITY_RESULTS")
            assert similar.mode == "DRAFT" and similar.draftId == draft.draftId
            for conversation_id in (cid, document_cid):
                histories[conversation_id] = (await client.get(f"{BASE}/conversations/{conversation_id}/messages?pageSize=100")).json()
            snapshots = [e["payload"] for m in histories[document_cid]["items"] for e in m["uiEvents"] if e["type"] == "REQUEST_DRAFT"]
            assert any(f["field"] == "producto_destino.mercado" and f["normalizedValue"] == "CHINA" for f in snapshots[0]["fields"])
            assert any(f["field"] == "producto_destino.mercado" and f["normalizedValue"] == "BRASIL" for f in snapshots[-1]["fields"])
            await client.post(BASE + "/auth/logout")
            await client.post(BASE + "/auth/login", json={"email": "admin-smoke@example.test", "password": password})
            report["admin"] = []
            for conversation_id in (cid, document_cid):
                detail = (await client.get(f"{BASE}/admin/conversations/{conversation_id}")).json()
                assert all(r["status"] == "COMPLETED" for r in detail["runs"])
                report["admin"].append({"runs": len(detail["runs"]), "tools": len(detail["toolExecutions"]),
                    "scopeMs": [r["scope_latency_ms"] for r in detail["runs"]],
                    "toolMs": [t["duration_ms"] for t in detail["toolExecutions"]]})
                events = (await client.get(BASE + "/admin/audit-events", params={"conversationId": conversation_id, "pageSize": 100})).json()["items"]
                report["admin"][-1]["uiPerformance"] = [e["metadata_json"] for e in events if e["event_type"] == "AGENT_RUN_COMPLETED"]
        app = create_app(config)
        async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://smoke") as client:
            await client.post(BASE + "/auth/login", json={"email": email, "password": password})
            original_send = httpx.AsyncClient.send
            async def isolated_send(instance, *args, **kwargs):
                assert isinstance(instance._transport, httpx.ASGITransport), "History attempted outbound HTTP"
                return await original_send(instance, *args, **kwargs)
            with patch.object(httpx.AsyncClient, "send", isolated_send), patch.object(app.state.platform.runtime, "execute", side_effect=AssertionError("No agent")), \
                patch.object(app.state.platform.runtime.sessions, "get_session", side_effect=AssertionError("No ADK history")), \
                patch.object(app.state.container.attachments, "get", side_effect=AssertionError("No intake lookup")):
                for conversation_id, expected in histories.items():
                    actual = await client.get(f"{BASE}/conversations/{conversation_id}/messages?pageSize=100")
                    assert actual.status_code == 200 and actual.json() == expected
            report["historyWithoutDependencies"] = True
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
