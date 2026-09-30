# Etapa 6B — entrega y checkpoint

Fecha: 2026-09-30. Implementación en este repositorio, bajo `apps/agent/`.
Se reutilizó la credencial OpenAI existente con autorización explícita; no se
crearon ni mostraron claves. No se inició Angular ni ninguna mutación de artículos.

## Entrega solicitada (33 puntos)

1. **HTTP:** autenticación, conversaciones, mensajes, adjuntos, borradores y
   administración; todos los endpoints para Angular tienen requests/responses/
   errors explícitos. [Referencia HTTP](../contracts/application-api-v1.md).
2. **Versionado:** `/api/v1`, OpenAPI 3.1; URLs 6A sin prefijo son aliases ocultos.
   Migración de respuestas 6A a DTOs V1 documentada, no silenciosa. Sin consumidor
   Angular previo. Futuras incompatibilidades requieren nueva versión/migración.
3. **DTOs:** `platform/contracts.py` define transportes públicos separados de
   ORM/ADK/Catalog. Admin tiene schemas propios; `mappers.py` proyecta registros.
4. **MessageDto:** id, conversationId, role, messageType, text, attachments,
   uiEvents, createdAt. Incluye SYSTEM_EVENT para intake; no raw ADK/tool result.
5. **ConversationSummaryDto:** id/title/status/preview/createdAt/updatedAt/
   lastMessageAt; sidebar por actividad y preview determinístico, sin LLM.
6. **ConversationDetail:** mismo DTO de metadata + GET messages paginado; evita
   duplicar historial. Admin detail agrega owner/org/runs/tools.
7. **AttachmentDto:** nombre original, MIME/type/size/status/createdAt/error y
   transcription nullable persistida. Sin storage key/path. Referencias nuevas
   guardadas como snapshots en Application DB mediante migración 0004.
8. **SendMessageRequest:** UUID clientMessageId, text nullable y attachmentIds;
   requiere texto o adjuntos propios READY. Valida duplicados y límites.
9. **SendMessageResponse:** userMessage, assistantMessage nullable, run mínimo
   id/status/error. STARTED sólo para retry concurrente; normalmente COMPLETED.
   Conserva idempotencia, incluidos IDs/eventos y ausencia de reejecución.
10. **UiEventDto:** id/messageId/type/schemaVersion1/sequence/payload/createdAt;
    unión discriminada, payloads tipados y orden explícito persistido.
11. **Tipos:** ARTICLE_SEARCH_RESULTS, ARTICLE_DETAIL, ARTICLE_COMPARISON,
    SIMILARITY_RESULTS, TECHNICAL_SHEET, REQUEST_DRAFT, SAVED_FILTER_LIST,
    SAVED_FILTER_CREATED, SAVED_FILTER_DELETED, ATTACHMENT_STATUS, ERROR.
12. **Arquitectura presenter:** funciones puras + registro de payloads → plugin
    de tools captura datos y métricas → Platform valida/persiste junto al
    assistant/run. Intake crea SYSTEM_EVENT. No parsea narrativa ni hace llamadas
    adicionales al catálogo para decorar tarjetas.
13. **Mappings:** [tabla tool/event/componente](../contracts/ui-events-v1.md).
    Metadata produce 0 eventos; lista/get para resolver filtro antes de execute
    se suprimen, dejando resultados de búsqueda. Delete preserva nombre real.
14. **Search:** query/total/page/pageSize/articles; filtros con paths/labels/values.
    Proyección compacta sin atributos inventados; ausentes null.
15. **Detail:** article code/name + grupos/fields/values/displayValue, sin metadata
    interna ni raw DTO. Grupos identificación/producto/códigos/envase/etiqueta/
    fechas/comercial/calidad cuando existen.
16. **Comparison:** articles/rows con values por código y SAME/DIFFERENT copiado
    de Catalog, no calculado por UI. Conserva orden y nulls.
17. **Similarity:** REFERENCE/FEATURES/DRAFT, IDs, criterios usados/ignorados,
    candidatos separados, score/eligibility y evaluaciones MATCH/MISMATCH/
    NOT_AVAILABLE/required. Preservados 900004/90/INELIGIBLE y 900006/70/ELIGIBLE.
    Cero elegibles permanece []; no sustituye aptos por no aptos.
18. **Sheet:** metadatos explícitos; documentAvailable:false y documentId:null.
    No PDF ni documento ficticio.
19. **Draft:** draftId/status/fields/updatedAt, estados cerrados y provenance
    PDF/page, XLSX/sheet/cell, USER sin notas internas. Correcciones generan nuevo
    snapshot y conservan el anterior.
20. **Filtros:** lista/created/deleted con SavedFilterView id/name/criteria/fechas,
    sin owner IDs internos. Identidad demo proviene del usuario autenticado.
21. **Errores:** error.code/message/requestId y header correlacionado; safe HTTP
    también para validación, 404, catálogo, intake y fallas inesperadas. Run FAILED
    no inventa respuesta assistant. PROVIDER_UNAVAILABLE/RATE_LIMITED reservados.
22. **Paginación:** items/page/pageSize/total, 1..100, mensajes ASC con id como
    desempate. Archive readable; bloquea mensajes nuevos y escrituras de intake.
23. **OpenAPI:** exportado y validado por tests; esquemas específicos de éxito,
    errores y paginación, enums y unión de 11 eventos. CookieSession documentado
    como apiKey en cookie; password writeOnly. Listo para generar tipos TS.
24. **Fixtures:** 19 JSON validados/regenerables, incluidos los 13 mínimos
    solicitados y mensajes/event envelope/created/deleted/status/error UI.
    [Ejemplos](../contracts/examples/). `npm run agent:contracts:export` no llama APIs.
25. **Tests nuevos:** 39 casos de contratos/proyecciones/fixtures/privacidad,
    scores/eligibility/ausentes, provenance/statuses, ruido de filtros,
    idempotencia/persistencia/inmutabilidad/restart/chronological pages,
    audio/transcript/attachment-only, draft corrections, auth/CORS/UTC/Swagger.
    Se actualizó la regresión 6A para privacidad/error.requestId y draftId público.
26. **Resultados:** 121 agent tests aprobados (119 determinísticos + 2 integración
    Catalog), 5 live omitidos para evitar llamadas pagas redundantes; Catalog
    unit 5 y E2E 17 aprobados. Total 143 aprobados; build Catalog aprobado.
27. **OpenAI real:** una ejecución representativa, cuatro turnos de catálogo
    (search/detail/similarity/sheet), cuatro runs COMPLETED y cinco tools (incluye
    lectura necesaria del referente), con UiEvents/relaciones/audit correctos.
28. **Documento real:** un XLSX, extracción de corte/mercado/temperatura como
    PROPOSED; corrección conversacional CHINA → BRASIL, luego similitud DRAFT
    explícita incluyendo propuestas. Dos runs COMPLETED y tres tools. Dos
    REQUEST_DRAFT en turno de corrección: lectura previa + snapshot corregido.
29. **Reconstruction:** ambos historiales conservados tras cerrar/reabrir
    Application API sobre las mismas DBs temporales, con igualdad JSON exacta.
30. **Sin dependencias:** bloqueados HTTP saliente (OpenAI/Catalog), runtime.execute,
    sessions.get_session e Intake lookup; ambos historiales siguen funcionando
    sólo desde Application DB. También probado con comparación y vista admin
    mediante runtime ADK real + modelo determinístico.
31. **Regresiones detectadas/corregidas:** camelización del cliente alteraba keys
    de paths canónicos dentro de criterios; se preservan dotted keys. OpenAPI
    V1 debía incluir explícitamente router de plataforma (FastAPI router diferido).
    Pagination mensajes se seleccionaba DESC y luego invertía sólo cada página:
    ahora ASC desde consulta. Public responses 6A exponían internals: separados.
    Se agregó migración 0004 incremental para references, sin reescribir una
    migración 0003 ya aplicada por el servidor en reload.
    **Entorno:** Docker existente en 3000 está desactualizado y omite metadata
    used_for_similarity/can_be_required. Integración falló allí; pasó con source
    actual en instancia temporal 3001. No se reemplazó el Docker del usuario.
32. **Deuda:** Scope baseline ~2,12 s y FAIL_OPEN (revisar antes de mutations);
    SSO/MFA/password reset, edge rate limit, antivirus, object storage,
    encryption/retention, restringir Swagger público; abrupt STARTED necesita
    reconciliación administrativa; Git con reestructuración previa extensa;
    warning ADK JSON Schema experimental. Referencias pre-V1 sin snapshot usan
    Intake DB. No se agregaron jobs/reconciliation ni soluciones fuera de 6B.
33. **6C:** generar tipos/client desde OpenAPI, login/cookies withCredentials,
    sidebar/historial/composer y renderer discriminado UiEvents. Usar tarjetas
    persistidas como datos, narrativa como texto; no recalcular elegibilidad,
    comparisons ni snapshots. Actualizar imagen del catálogo antes de probar
    documentos/similitud con el servicio habitual. **STOP: Angular no iniciado.**

## Evidencia y rendimiento

[`smoke-6b-result.json`](../contracts/smoke-6b-result.json) resume las aserciones de
la ejecución real, sin credenciales ni prompts. POSTs de catálogo ~4,59–12,99 s;
Scope ~1,15–2,71 s en esta muestra; tool callbacks ~1,41–25,12 ms.
Presenters ~0,05–3,24 ms/run; inserción/flush UI ~0,25–0,81 ms (sin commit final).
La capa UI no agrega latencia significativa frente al modelo/Scope en esta
muestra; no es un benchmark de producción ni estimación p95.

El requerimiento de congelar datos no implica demostrar que cada frase del LLM
sea correcta: DTOs y evaluaciones hacen verificables los datos representados.
El catálogo sigue siendo sintético, no constituye validación de datos reales.

## Operación

Application API habitual: `npm run agent:api`; Swagger `/docs`, contrato `/api/v1`.
No existe frontend Angular todavía. Para actualizar el Docker del catálogo:
`docker compose -f apps/catalog-api/docker-compose.yml up -d --build` (no borrar
volúmenes; ésta es una instrucción de operación, no se ejecutó en este checkpoint).
Alternativa local actual: `npm run api:dev` si 3000 está libre, o PORT distinto
coherente con CATALOG_API_BASE_URL. El smoke usó 3001 sólo temporalmente.

No se hicieron commits: preserve y revise la reestructuración previa del
working tree antes de seleccionar archivos. Migraciones aplican al iniciar API;
no requiere reset ni borrar conversaciones anteriores.
