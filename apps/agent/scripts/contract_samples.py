"""Reproducible, synthetic contract examples from the demo seed (no API calls)."""
import json
from pathlib import Path
from solvo_client_agent.clients.catalog_api import _camelize
from solvo_client_agent.platform import contracts as c, presenters as p

ROOT = Path(__file__).resolve().parents[3]
STAMP = "2026-09-30T12:00:00Z"
SEARCH = {"filters": [{"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"},
    {"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"}]}


def article(code="900001"):
    seed = json.loads((ROOT / "apps/catalog-api/data/seed/articles.v1.json").read_text())
    return next(d for d in seed if d["identificacion"]["codigo"] == code)


def search_result():
    a = article()
    return _camelize({"items": [{**a["identificacion"], **a["producto_destino"], **a["envase_pesaje"]}],
        "pagination": {"page": 1, "page_size": 20, "total_items": 1, "total_pages": 1}})


def compare_result():
    a, b = article(), article("900002")
    fields = []
    for field in ("identificacion.nombre", "identificacion.especie", "producto_destino.temperatura"):
        group, key = field.split(".")
        values = {"900001": a[group][key], "900002": b[group][key]}
        fields.append({"field": field, "values": values, "different": values["900001"] != values["900002"]})
    return _camelize({"compared_codes": ["900001", "900002"], "fields": fields})


def similar_result():
    def candidate(code, score, eligibility):
        a = article(code)
        return {"codigo": code, "similarityScore": score, "eligibility": eligibility,
            "weightedEvaluation": [{"field": "identificacion.especie", "referenceValue": "BOVINO",
                "candidateValue": a["identificacion"]["especie"], "status": "MATCH"}],
            "requiredEvaluation": [{"field": "producto_destino.temperatura", "requiredValue": "CONGELADO",
                "candidateValue": a["producto_destino"]["temperatura"], "status": "MATCH" if code == "900006" else "MISMATCH"}]}
    return {"result": {"criteriaUsed": {"weighted": {"identificacion.especie": "BOVINO"},
        "required": {"producto_destino.temperatura": "CONGELADO"}},
        "eligibleCandidates": [candidate("900006", 70, "ELIGIBLE")],
        "ineligibleCandidates": [candidate("900004", 90, "INELIGIBLE")]}}


def sheet_result():
    seed = json.loads((ROOT / "apps/catalog-api/data/seed/technical-sheets.v1.json").read_text())
    return _camelize(seed[0])


def draft_result():
    return {"id": "draft_example", "status": "NEEDS_REVIEW", "updated_at": STAMP,
        "fields": [{"field": "producto_destino.mercado", "raw_value": "China", "normalized_value": "CHINA",
            "status": "PROPOSED", "required": True,
            "source": {"type": "SPREADSHEET", "attachment_id": "att_example", "sheet": "Pedido", "cell": "B2"}}]}


def filter_result():
    return {"id": "filter_example", "name": "China", "search": SEARCH,
        "created_at": STAMP, "updated_at": STAMP, "owner_user_id": "DO_NOT_EXPOSE"}


def attachment_result():
    return {"id": "att_example", "original_filename": "pedido.xlsx", "filename": "INTERNAL_STORAGE_KEY",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "type": "SPREADSHEET", "status": "READY", "size_bytes": 5300, "created_at": STAMP}


def examples():
    state = {"current_search": SEARCH}
    search = p.present("search_articles", {"ok": True, "data": search_result()}, {}, state)[0][1]
    detail = p.article_detail(_camelize(article()))
    comparison = p.comparison(compare_result())
    similar = p.similarity(similar_result(), {"reference_code": "900001"}, {})
    sheet = p.present("get_technical_sheet", {"ok": True, "data": sheet_result()}, {}, {})[0][1]
    draft = p.draft(draft_result())
    filters = c.SavedFilterListPayload(filters=[p.saved_filter(filter_result())])
    att = p.attachment(attachment_result())
    event = p.EVENT_ADAPTER.validate_python({"id": "event_example", "messageId": "message_assistant",
        "type": "ARTICLE_SEARCH_RESULTS", "schemaVersion": 1, "sequence": 1, "createdAt": STAMP, "payload": search})
    user = c.MessageDto(id="message_user", conversationId="conversation_example", role="USER", messageType="TEXT",
        text="Buscame bife ancho para China.", attachments=[], uiEvents=[], createdAt=STAMP)
    assistant = c.MessageDto(id="message_assistant", conversationId="conversation_example", role="ASSISTANT", messageType="TEXT",
        text="Encontré un artículo: 900001 — Bife ancho congelado CHINA.", attachments=[], uiEvents=[event], createdAt=STAMP)
    conversation = c.ConversationSummaryDto(id="conversation_example", title=user.text, status="ACTIVE",
        preview=assistant.text, createdAt=STAMP, updatedAt=STAMP, lastMessageAt=STAMP)
    return {"auth-me": c.CurrentUserDto(id="user_example", email="demo@example.test", role="CLIENT_USER",
            organization=c.OrganizationView(id="org_example", name="Organización de ejemplo")),
        "conversation-list": c.PageDto[c.ConversationSummaryDto](items=[conversation], page=1, pageSize=20, total=1),
        "conversation-detail": conversation,
        "conversation-messages": c.PageDto[c.MessageDto](items=[user, assistant], page=1, pageSize=20, total=2),
        "send-message-response": c.SendMessageResponse(userMessage=user, assistantMessage=assistant,
            run=c.AgentRunSummaryDto(id="run_example", status="COMPLETED", error=None)),
        "article-search-results": search, "article-detail": detail, "article-comparison": comparison,
        "similarity-results": similar, "technical-sheet": sheet, "request-draft": draft,
        "saved-filter-list": filters, "saved-filter-created": c.SavedFilterCreatedPayload(filter=filters.filters[0]),
        "saved-filter-deleted": c.SavedFilterDeletedPayload(id="filter_example", name="China"),
        "attachment": att, "attachment-status": c.AttachmentStatusPayload(attachment=att),
        "ui-event": event, "error-ui-event": c.ErrorUiPayload(code="CATALOG_UNAVAILABLE", message="El catálogo no está disponible.", retryable=True),
        "api-error": c.ApiError(error=c.HttpError(code="CONVERSATION_NOT_FOUND", message="La conversación no existe.", requestId="req_example"))}
