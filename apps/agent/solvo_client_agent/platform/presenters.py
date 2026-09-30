"""Deterministic projections of validated tool results; no model, HTTP or ORM here."""
import json
import re
from pydantic import TypeAdapter
from . import contracts as c

EVENTS = {
    "ARTICLE_SEARCH_RESULTS": c.ArticleSearchResultsPayload,
    "ARTICLE_DETAIL": c.ArticleDetailPayload,
    "ARTICLE_COMPARISON": c.ArticleComparisonPayload,
    "SIMILARITY_RESULTS": c.SimilarityResultsPayload,
    "TECHNICAL_SHEET": c.TechnicalSheetPayload,
    "REQUEST_DRAFT": c.RequestDraftPayload,
    "SAVED_FILTER_LIST": c.SavedFilterListPayload,
    "SAVED_FILTER_CREATED": c.SavedFilterCreatedPayload,
    "SAVED_FILTER_DELETED": c.SavedFilterDeletedPayload,
    "ATTACHMENT_STATUS": c.AttachmentStatusPayload,
    "ERROR": c.ErrorUiPayload,
}
EVENT_ADAPTER = TypeAdapter(c.UiEventDto)
LABELS = {"codigo": "Código", "nombre": "Nombre", "especie": "Especie",
    "grupo_anatomico": "Grupo anatómico", "corte": "Corte", "mercado": "Mercado",
    "pais_destino": "País de destino", "temperatura": "Temperatura",
    "presentacion": "Presentación", "envase_primario": "Envase primario",
    "envase_exterior": "Envase exterior", "activo": "Activo"}
GROUPS = {"identificacion": ("identification", "Identificación"),
    "producto_destino": ("productDestination", "Producto y destino"),
    "codigos_asociaciones": ("codesAssociations", "Códigos y asociaciones"),
    "envase_pesaje": ("packagingWeight", "Envase y pesaje"),
    "etiquetado": ("labeling", "Etiquetado"),
    "fechas_operacion": ("datesOperation", "Fechas y operación"),
    "comercial_operativo": ("commercialOperation", "Información comercial"),
    "calidad_seguridad": ("qualitySafety", "Calidad y seguridad")}


def snake(value):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def normalized(data):
    # Normalize wire member names, but never transform domain field-path keys.
    if isinstance(data, dict):
        return {(snake(k) if "." not in k else k): normalized(v) for k, v in data.items()}
    if isinstance(data, list):
        return [normalized(v) for v in data]
    return data


def label(path):
    key = path.split(".")[-1]
    return LABELS.get(key, key.replace("_", " ").capitalize())


def display(value):
    if value is None:
        return "No disponible"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def search_summary(data):
    if data is None:
        return None
    return c.SearchSummary(filters=[c.SearchFilter(field=f["field"], label=label(f["field"]),
        operator=f["operator"], value=f.get("value"), displayValue=display(f.get("value")))
        for f in data.get("filters", [])])


def article_list(data):
    d = normalized(data)
    i, p, e = d.get("identificacion", d), d.get("producto_destino", d), d.get("envase_pesaje", d)
    return c.ArticleListItem(code=str(i["codigo"]), name=i.get("nombre"), species=i.get("especie"),
        anatomicalGroup=i.get("grupo_anatomico"), cut=p.get("corte"), market=p.get("mercado"),
        destinationCountry=p.get("pais_destino"), temperature=p.get("temperatura"),
        presentation=p.get("presentacion"), primaryPackaging=e.get("envase_primario"), active=i.get("activo"))


def article_detail(data):
    d = normalized(data)
    compact = article_list(d)
    groups = [c.ArticleGroup(key=key, label=title, fields=[c.DisplayField(field=f"{group}.{field}",
        label=label(field), value=value, displayValue=display(value)) for field, value in d[group].items()])
        for group, (key, title) in GROUPS.items() if isinstance(d.get(group), dict)]
    return c.ArticleDetailPayload(article=c.ArticleView(code=compact.code, name=compact.name, groups=groups))


def comparison(data):
    d = normalized(data)
    codes = d["compared_codes"]
    names = next((f["values"] for f in d["fields"] if f["field"] == "identificacion.nombre"), {})
    return c.ArticleComparisonPayload(articles=[c.ComparedArticle(code=str(code), name=names.get(str(code))) for code in codes],
        rows=[c.ComparisonRow(field=f["field"], label=label(f["field"]),
            status="DIFFERENT" if f["different"] else "SAME", values=[c.ComparisonValue(articleCode=str(code),
            value=f["values"].get(str(code)), displayValue=display(f["values"].get(str(code)))) for code in codes])
            for f in d["fields"]])


def similarity(data, args, state):
    d = normalized(data)
    result = d.get("result", d)
    context = state.get("last_similarity", {})
    mode = context.get("mode") or ("draft" if args.get("use_current_draft") else "reference" if args.get("reference_code") else "features")
    used = result["criteria_used"]
    criteria = [c.UsedCriterion(field=f, label=label(f), value=v, displayValue=display(v), required=required)
        for section, required in (("weighted", False), ("required", True)) for f, v in used.get(section, {}).items()]
    def candidate(item):
        evaluations = [c.SimilarityCriterion(field=e["field"], label=label(e["field"]),
            expectedValue=e.get("required_value") if required else e.get("reference_value"),
            expectedDisplayValue=display(e.get("required_value") if required else e.get("reference_value")),
            actualValue=e.get("candidate_value"), actualDisplayValue=display(e.get("candidate_value")),
            required=required, status=e["status"])
            for section, required in (("weighted_evaluation", False), ("required_evaluation", True))
            for e in item.get(section, [])]
        # Use only values actually present in the evaluations. Do not fetch more
        # articles just to decorate a card or pretend a missing name is known.
        projection = {"identificacion": {"codigo": str(item["codigo"])} }
        for e in evaluations:
            if "." in e.field:
                group, field = e.field.split(".", 1)
                projection.setdefault(group, {})[field] = e.actualValue
        return c.SimilarityCandidate(article=article_list(projection), score=item["similarity_score"],
            eligibility=item["eligibility"], criteria=evaluations)
    reasons = {"field_not_supported_for_similarity": "NOT_SUPPORTED_FOR_SIMILARITY", "required_not_supported": "NOT_SUPPORTED_FOR_SIMILARITY",
        "status_proposed_not_active": "UNCONFIRMED", "status_rejected_not_active": "REJECTED",
        "status_needs_clarification_not_active": "NEEDS_CLARIFICATION",
        "unsupported_field": "NOT_SUPPORTED_FOR_SIMILARITY", "not_similarity_field": "NOT_SUPPORTED_FOR_SIMILARITY",
        "not_supported_for_similarity": "NOT_SUPPORTED_FOR_SIMILARITY", "unconfirmed": "UNCONFIRMED",
        "proposed_not_included": "UNCONFIRMED", "rejected": "REJECTED", "needs_clarification": "NEEDS_CLARIFICATION"}
    ignored = [c.IgnoredCriterion(field=v["field"], label=label(v["field"]), value=v.get("value"),
        reason=reasons.get(v.get("reason"), "OTHER")) for v in d.get("draft_mapping", {}).get("ignored_fields", [])]
    return c.SimilarityResultsPayload(mode=mode.upper(), referenceArticleCode=context.get("reference_code", args.get("reference_code")),
        draftId=context.get("draft_id"), usedCriteria=criteria, ignoredCriteria=ignored,
        eligibleCandidates=[candidate(v) for v in result["eligible_candidates"]],
        ineligibleCandidates=[candidate(v) for v in result["ineligible_candidates"]])


def draft(data):
    d = normalized(data)
    fields = []
    for f in d["fields"]:
        source = f["source"]
        public_source = {"type": source["type"]}
        if source["type"] != "USER":
            public_source["attachmentId"] = source["attachment_id"]
            public_source.update({key: source[key] for key in ("page", "sheet", "cell") if key in source})
        fields.append(c.DraftFieldDto(field=f["field"], label=label(f["field"]), rawValue=f["raw_value"],
            normalizedValue=f.get("normalized_value"), displayValue=display(f.get("normalized_value")),
            status=f["status"], required=f["required"], source=public_source))
    return c.RequestDraftPayload(draftId=d["id"], status=d["status"], fields=fields, updatedAt=d["updated_at"])


def saved_filter(data):
    d = normalized(data)
    return c.SavedFilterView(id=d["id"], name=d["name"], criteria=search_summary(d["search"]),
        createdAt=d["created_at"], updatedAt=d["updated_at"])


def attachment(data):
    d = normalized(data)
    return c.AttachmentDto(id=d["id"], filename=d["original_filename"], mimeType=d["mime_type"], type=d["type"],
        sizeBytes=d["size_bytes"], status=d["status"], createdAt=d["created_at"],
        error=c.SafeError(code=d["error_code"], message="No se pudo procesar el adjunto.") if d.get("error_code") else None,
        transcription=d.get("transcription"))


def present(name, result, args, state):
    """0..N payloads, validated before persistence. Never consume assistant prose."""
    if not result.get("ok", True):
        error = result.get("error", {})
        return [("ERROR", c.ErrorUiPayload(code=error.get("code", "TOOL_EXECUTION_FAILED"),
            message="No se pudo completar la consulta.", retryable=bool(error.get("retryable", False))))]
    d = normalized(result.get("data", {}))
    if name in {"search_articles", "execute_saved_filter"}:
        p = d["pagination"]
        return [("ARTICLE_SEARCH_RESULTS", c.ArticleSearchResultsPayload(query=search_summary(state.get("current_search")),
            total=p["total_items"], page=p.get("page", args.get("page", 1)),
            pageSize=p.get("page_size", args.get("page_size", 20)), articles=[article_list(v) for v in d["items"]]))]
    if name == "get_article":
        return [("ARTICLE_DETAIL", article_detail(d))]
    if name == "compare_articles":
        return [("ARTICLE_COMPARISON", comparison(d))]
    if name == "find_similar_articles":
        return [("SIMILARITY_RESULTS", similarity(d, args, state))]
    if name == "get_technical_sheet":
        return [("TECHNICAL_SHEET", c.TechnicalSheetPayload(sheet=c.TechnicalSheetView(id=d["ficha_id"],
            articleCode=d["articulo_codigo"], title=d.get("titulo"), version=d.get("version"), language=d.get("idioma"),
            status=d.get("estado"), createdAt=d.get("created_at"), updatedAt=d.get("updated_at"), sourceNote=d.get("source_note"))))]
    if name in {"get_request_draft", "update_request_draft", "review_request_draft"}:
        return [("REQUEST_DRAFT", draft(d))]
    if name in {"list_saved_filters", "get_saved_filter"}:
        return [("SAVED_FILTER_LIST", c.SavedFilterListPayload(filters=[saved_filter(v) for v in d["items"]] if "items" in d else [saved_filter(d)]))]
    if name == "save_filter":
        return [("SAVED_FILTER_CREATED", c.SavedFilterCreatedPayload(filter=saved_filter(d)))]
    if name == "delete_saved_filter":
        return [("SAVED_FILTER_DELETED", c.SavedFilterDeletedPayload(id=d["id"], name=d["name"]))]
    return []


def final_events(pending):
    # A list used only to resolve a filter name is not a user-facing result.
    executes = [i for i, (name, _, _) in enumerate(pending) if name == "execute_saved_filter"]
    return [(kind, payload) for i, (name, kind, payload) in enumerate(pending)
        if not (name in {"list_saved_filters", "get_saved_filter"} and any(j > i for j in executes))]
