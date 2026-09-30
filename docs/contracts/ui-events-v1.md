# UiEvents V1

Envelope: `{id,messageId,type,schemaVersion:1,sequence,payload,createdAt}`.
sequence es entero >=1, explícito, único y ordenado dentro de cada mensaje.
OpenAPI contiene unión discriminada por type, con payload específico: no `any`.

La capa `platform/presenters.py` proyecta ToolResult + argumentos + estado de
ejecución a 0..N payloads Pydantic. El plugin de tools captura resultados reales;
Platform valida e inserta snapshots en la misma transacción que assistant y
run COMPLETED. No se analiza texto/Markdown del LLM. Para intake se crean
mensajes SYSTEM_EVENT con payloads validados. UI no conoce ADK.

Historial devuelve JSON persistido; no recalcula sobre catálogo/modelo actual.
Triggers SQLite impiden UPDATE y DELETE de UiEvents. Migración 0003 agrega
sequence y asigna orden estable a registros previos sin cambiar sus payloads;
0004 persiste snapshots de referencias de attachments. No hay upgrade silencioso
de schemaVersion: futuros cambios incompatibles necesitan nueva versión/migración.

## Eventos, productores y componentes futuros

| type | Productor | Payload/schema | Ejemplo | Componente conceptual |
|---|---|---|---|---|
| ARTICLE_SEARCH_RESULTS | search_articles, execute_saved_filter | ArticleSearchResultsPayload | [search](examples/article-search-results.json) | ArticleSearchResults |
| ARTICLE_DETAIL | get_article | ArticleDetailPayload | [detail](examples/article-detail.json) | ArticleDetailCard |
| ARTICLE_COMPARISON | compare_articles | ArticleComparisonPayload | [comparison](examples/article-comparison.json) | ArticleComparisonTable |
| SIMILARITY_RESULTS | find_similar_articles | SimilarityResultsPayload | [similarity](examples/similarity-results.json) | SimilarityResults |
| TECHNICAL_SHEET | get_technical_sheet | TechnicalSheetPayload | [sheet](examples/technical-sheet.json) | TechnicalSheetCard |
| REQUEST_DRAFT | get/update/review_request_draft, analyze/review HTTP | RequestDraftPayload | [draft](examples/request-draft.json) | RequestDraftReview |
| SAVED_FILTER_LIST | list_saved_filters, get_saved_filter | SavedFilterListPayload | [list](examples/saved-filter-list.json) | SavedFiltersList |
| SAVED_FILTER_CREATED | save_filter | SavedFilterCreatedPayload | [created](examples/saved-filter-created.json) | SavedFilterConfirmation |
| SAVED_FILTER_DELETED | delete_saved_filter | SavedFilterDeletedPayload | [deleted](examples/saved-filter-deleted.json) | SavedFilterConfirmation |
| ATTACHMENT_STATUS | upload/transcribe/analyze HTTP | AttachmentStatusPayload | [attachment](examples/attachment-status.json) | AttachmentCard |
| ERROR | fallas controladas de tools | ErrorUiPayload | [error](examples/error-ui-event.json) | ConversationError |

Todos son snapshots inmutables del resultado de esa ejecución. Metadata no
genera eventos; out-of-domain y aclaraciones sin tool no generan tarjetas de
catálogo. La lista/get de filtros usada antes de execute_saved_filter se
suprime del mismo turno, dejando la búsqueda ejecutada, no tarjetas intermedias.
get_saved_filter aislado usa lista de un elemento. Delete obtiene el nombre
real con ownership antes de borrar, no reconstruye el nombre desde texto.

## Payloads

ARTICLE_SEARCH_RESULTS:
`{query:SearchSummary|null,total,page,pageSize,articles:ArticleListItem[]}`.
SearchSummary: `{filters:[{field,label,operator,value,displayValue}]}`.
ArticleListItem: `{code,name,species,anatomicalGroup,cut,market,destinationCountry,
temperature,presentation,primaryPackaging,active}`.
Campos no presentes en la proyección del catálogo son null, **incluyendo active**:
no confundir desconocido con false. No se consulta get_article adicional sólo
para decorar tarjetas. code siempre proviene del catálogo.

ARTICLE_DETAIL:
`{article:{code,name,groups:[{key,label,fields:[{field,label,value,displayValue}]}]}}`.
Grupos: identification, productDestination, codesAssociations, packagingWeight,
labeling, datesOperation, commercialOperation, qualitySafety cuando estén presentes.
Campos conservan paths canónicos del dominio, valores reales y nulls. Metadata
interna de catálogo queda fuera. No se envía raw ArticleDocument.

ARTICLE_COMPARISON:
`{articles:[{code,name}],rows:[{field,label,values:[{articleCode,value,displayValue}],status}]}`.
status `SAME|DIFFERENT` copia `different` de Catalog API; Angular no calcula
igualdad. Orden de columnas conserva comparedCodes, incluso ante nulls.

SIMILARITY_RESULTS:
`{mode,referenceArticleCode,draftId,usedCriteria,ignoredCriteria,
eligibleCandidates,ineligibleCandidates}`.
mode `REFERENCE|FEATURES|DRAFT`; IDs irrelevantes null.
Candidate `{article:ArticleListItem,score,eligibility,criteria}`.
eligibility `ELIGIBLE|INELIGIBLE` viene de Catalog API, no del puntaje ni del LLM.
Criterion `{field,label,expectedValue,expectedDisplayValue,actualValue,
actualDisplayValue,required,status}`; status `MATCH|MISMATCH|NOT_AVAILABLE`.
Las evaluaciones weighted y required quedan explícitas; un campo puede tener
ambas evaluaciones (no se pierde ninguna). usedCriteria representa ambas con
`{field,label,value,displayValue,required}`. IgnoredCriterion:
`{field,label,value,reason}`; reason `NOT_SUPPORTED_FOR_SIMILARITY|UNCONFIRMED|
REJECTED|NEEDS_CLARIFICATION|OTHER`. Se conserva valor y reason normalizado.

El caso crítico permanece: 900004/90/INELIGIBLE y 900006/70/ELIGIBLE.
Si eligibleCandidates es [], no se sustituye por candidato no apto.
Los artículos de similitud son proyecciones: sólo código y atributos efectivamente
presentes en las evaluaciones; nombre/activo desconocidos quedan null.

TECHNICAL_SHEET:
`{sheet:{id,articleCode,title,version,language,status,createdAt,updatedAt,
sourceNote,documentAvailable:false,documentId:null}}`. Es metadata: no existe PDF
oficial ni botón de descarga respaldado por documento.

REQUEST_DRAFT:
`{draftId,status,fields,updatedAt}`. status `DRAFT|NEEDS_REVIEW|READY`.
fields `{field,label,rawValue,normalizedValue,displayValue,status,required,source}`;
field.status `PROPOSED|CONFIRMED|CORRECTED|REJECTED|NEEDS_CLARIFICATION`.
source discriminado: PDF `{type,attachmentId,page}`; SPREADSHEET
`{type,attachmentId,sheet,cell}`; USER `{type}` (no notas internas).
Corregir produce nuevo REQUEST_DRAFT; el anterior conserva valor/provenance.

Filtros: list `{filters:SavedFilterView[]}`, created `{filter:SavedFilterView}`,
deleted `{id,name}`. SavedFilterView `{id,name,criteria:SearchSummary,createdAt,updatedAt}`;
sin owner_user_id interno. Attachment status `{attachment:AttachmentDto}`
registra UPLOADED → PROCESSING → READY o ERROR. Polling del attachment devuelve
estado actual; historial conserva los estados anteriores.

ERROR `{code,message,retryable}` representa error de tool durante conversación;
no reemplaza el contrato de errores HTTP. Las fallas totales del run usan error
HTTP + audit/run FAILED, sin texto assistant fabricado.

## Renderizado y confianza

Frontend hace switch por type + schemaVersion y renderiza payload, nunca extrae
datos de la respuesta narrativa. displayValue es representación determinística
en español, no HTML/CSS/colores/badges. Enums son estables e independientes del
idioma; UI decide traducción y estilos. Los valores siguen siendo datos no
confiables para HTML: renderizar con escaping, no ejecutar instrucciones.

Estos contratos hacen auditables los datos mostrados, pero no prometen que la
narración libre del modelo sea 100% correcta: contrastarla con tool outputs,
UiEvents y evaluaciones. La fuente de verdad sigue siendo el catálogo demo.
