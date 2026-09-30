# Application API V1 — Etapa 6B

Contrato canónico: `http://127.0.0.1:3100/api/v1`. OpenAPI 3.1:
[`application-api-v1.openapi.json`](application-api-v1.openapi.json). Swagger en `/docs`.
Todos los DTOs se validan con Pydantic y rechazan campos adicionales. No son modelos
SQLAlchemy, eventos ADK ni respuestas crudas del catálogo. V1 no admite cambios
incompatibles silenciosos: nueva versión o migración explícita.

## Rutas públicas

| Método/ruta relativa a `/api/v1` | Respuesta |
|---|---|
| POST `/auth/login` | CurrentUserDto + cookie HttpOnly |
| POST `/auth/logout` | `{ok:true}`; revoca sesión y elimina cookie |
| GET `/auth/me` | CurrentUserDto |
| GET `/saved-filters` | SavedFilterListPayload; lectura autenticada y acotada al usuario |
| POST `/conversations` | ConversationSummaryDto, HTTP 201 |
| GET `/conversations` | PageDto<ConversationSummaryDto> |
| GET `/conversations/{id}` | ConversationSummaryDto; metadata, no historial duplicado |
| GET `/conversations/{id}/messages` | PageDto<MessageDto> |
| POST `/conversations/{id}/messages` | SendMessageResponse |
| POST `/conversations/{id}/archive` | ConversationSummaryDto |
| POST `/conversations/{id}/attachments` | multipart `file`; AttachmentDto, HTTP 201 |
| GET `/conversations/{id}/attachments/{attachmentId}` | AttachmentDto |
| POST `/conversations/{id}/attachments/{attachmentId}/transcribe` | AttachmentDto con transcription |
| POST `/conversations/{id}/attachments/{attachmentId}/analyze` | `{attachment:AttachmentDto,draft:RequestDraftPayload}` |
| GET `/conversations/{id}/drafts/{draftId}` | RequestDraftPayload |
| POST `/conversations/{id}/drafts/{draftId}/review` | RequestDraftPayload |

Login recibe `{email,password}`; password es `writeOnly` en OpenAPI.
CurrentUserDto: `{id,email,role,organization:{id,name}|null}`. Roles:
`CLIENT_USER`, `INTERNAL_ADMIN`. Nunca envía la identidad demo del catálogo.

Review recibe `{field,action,normalized_value?,required?,note?}`;
action `confirm|correct|reject`. Se conserva este request funcional de intake;
la respuesta pública usa camelCase. No acepta contenido HTML ni instrucciones de UI.

Los URLs sin prefijo de 6A permanecen como aliases operativos, fuera de OpenAPI.
La lectura `GET /saved-filters` se añadió de forma compatible en 6D para que el menú
pueda abrirse sin crear conversaciones vacías ni ejecutar al modelo. Reutiliza los
DTOs `SavedFilterListPayload`/`SavedFilterView` de 6B, resuelve la identidad del
catálogo sólo en servidor y no expone su encabezado `X-Demo-User-Id` al navegador.
**Migración explícita de 6A a 6B:** sus respuestas ahora son los DTOs V1, no las
columnas internas snake_case de 6A. Los scripts existentes fueron adaptados;
no existía cliente Angular. No utilizar aliases para consumidores nuevos.
Los endpoints intake antiguos `/attachments` y `/drafts` siguen deshabilitados
por defecto; sólo se habilitan explícitamente para pruebas de desarrollo.

## Contratos centrales

MessageDto:
`{id,conversationId,role,messageType,text,attachments,uiEvents,createdAt}`.
role: `USER|ASSISTANT|SYSTEM_EVENT`. messageType: `TEXT|AUDIO|DOCUMENT|SYSTEM`.
text puede ser null. AttachmentReferenceDto: `{id,filename,type,status}`.
Las referencias V1 son snapshots en Application DB; cambios posteriores del
adjunto no reescriben lo que se vio. Referencias pre-V1 sin snapshot conservan
un fallback de lectura a Intake DB, nunca a Catalog/ADK/OpenAI.

ConversationSummaryDto:
`{id,title,status,preview,createdAt,updatedAt,lastMessageAt}`.
status: `ACTIVE|ARCHIVED`. preview es el último texto visible, máximo 160
caracteres, sin llamadas LLM. Sidebar ordena `coalesce(lastMessageAt,createdAt)
DESC,id ASC`. ConversationDetail utiliza este mismo DTO y carga mensajes por
separado. Archivadas permiten lectura pero rechazan mensajes nuevos con 409;
no se implementa restore.

SendMessageRequest:
`{clientMessageId,text:null|string,attachmentIds:string[]}`.
clientMessageId es UUID; requiere texto significativo o adjuntos no repetidos,
máximo 20; texto máximo 20.000 caracteres. Los adjuntos deben ser propios de la
conversación y estar READY: transcribir audio o analizar documento primero.
Audio sin texto usa su transcripción; documento sin texto consulta el borrador.
Esto no convierte texto extraído en instrucciones confiables ni crea artículos.

SendMessageResponse:
`{userMessage:MessageDto,assistantMessage:MessageDto|null,run:{id,status,error}}`.
run.status: `STARTED|COMPLETED|FAILED`. El POST es síncrono normalmente COMPLETED;
un retry concurrente puede observar STARTED. No contiene scopes, prompts,
invocation IDs, provider/model ni trazas. El mismo conversationId/clientMessageId
y contenido devuelve los mismos IDs y snapshots sin ejecutar tools otra vez;
contenido distinto devuelve MESSAGE_DUPLICATE. Tras falla el retry muestra run
FAILED y assistantMessage null; no hay respuesta inventada ni reejecución automática.
Enviar una nueva intención/reintento autorizado requiere nuevo clientMessageId.

AttachmentDto:
`{id,filename,mimeType,type,sizeBytes,status,createdAt,error,transcription}`.
filename es el nombre original sanitizado, nunca el storage key. type:
`AUDIO|PDF|SPREADSHEET`; status: `UPLOADED|PROCESSING|READY|ERROR`.
transcription nullable se persiste una sola vez en el attachment (JSON de Intake
DB, compatible con registros antiguos). El evento READY contiene su snapshot;
no se agrega una copia adicional como texto del mensaje de audio. No se expone
filesystem path, conversation ownership interno ni proveedor de transcripción.

## Errores y paginación

Error HTTP uniforme: `{error:{code,message,requestId}}`; también
`X-Request-Id` en header. Una petición puede enviar un ID de 1–64 caracteres
alfanuméricos/guion/underscore; otros valores generan UUID. Errores de validación
no repiten inputs (incluyendo passwords), ni stacktrace/bytes/prompts.

| HTTP | Códigos y comportamiento |
|---|---|
| 401 | AUTH_REQUIRED, INVALID_CREDENTIALS (login genérico), SESSION_EXPIRED |
| 403 | FORBIDDEN, USER_DISABLED, ORGANIZATION_DISABLED, ATTACHMENT_ACCESS_DENIED |
| 404 | CONVERSATION_NOT_FOUND (incluye ownership ajeno), ATTACHMENT_NOT_FOUND, RUN_NOT_FOUND, NOT_FOUND |
| 409 | CONVERSATION_ARCHIVED, MESSAGE_DUPLICATE, MESSAGE_IN_PROGRESS, ATTACHMENT_NOT_READY |
| 422 | INVALID_MESSAGE, VALIDATION_ERROR y validación específica de campos/documentos |
| 413/415 | ATTACHMENT_TOO_LARGE / tipos de archivo no admitidos |
| 502 | AGENT_EXECUTION_FAILED; errores controlados de transcripción/extracción |
| 503 | CATALOG_UNAVAILABLE cuando falla el boundary HTTP de catálogo |
| 500 | INTERNAL_ERROR sin detalles internos |

PROVIDER_UNAVAILABLE queda reservado para una clasificación específica futura;
la ejecución actual usa AGENT_EXECUTION_FAILED. RATE_LIMITED queda reservado:
no se simula rate limiting. Los errores de tools pueden generar ERROR UiEvent
persistido con mensaje seguro; una falla total del run devuelve HTTP seguro y
run FAILED, sin falso assistant ni tarjeta adicional fabricada.

PageDto: `{items,page,pageSize,total}`; page>=1, pageSize=1..100 (default20).
Mensajes ordenan `createdAt ASC,id ASC`, incluyendo entre páginas. Historial
usa Application DB: no ejecuta providers, tools, presenters ni ADK. Todos los
timestamps públicos se serializan ISO8601 UTC (Z); UI localiza.

## Administración

Sólo INTERNAL_ADMIN: GET `/admin/organizations`, `/admin/users`,
`/admin/conversations`, `/admin/conversations/{id}`, `/admin/runs`,
`/admin/runs/{runId}`, `/admin/audit-events`. Listas usan PageDto.
Filtros ya disponibles en Swagger: organización/usuario/conversación/status,
scope/error/tool y rangos de fecha según recurso.

AdminOrganizationDto/AdminUserDto/AdminConversationDto/AdminAgentRunDto/
AdminToolExecutionDto/AdminAuditEventDto son contratos separados, con nombres
snake_case preservados para inspección de 6A. Run detail incluye run y mensajes
V1 + toolExecutions. Conversation detail incluye propietario, organización,
mensajes con UiEvents, runs y tools. Hay argumentos redactados y summaries,
nunca passwords, session token hashes, documento binario ni chain-of-thought.
Provider/model, IDs de correlación, scopes y latencias sólo van a administración.
Acceso a conversación/run administrativo se audita: el auditor también es auditado.

## Fuentes verificables

[`ui-events-v1.md`](ui-events-v1.md), [`angular-integration.md`](angular-integration.md),
[`examples/`](examples/) y el OpenAPI exportado. Regenerar con
`npm run agent:contracts:export`; tests comparan fixtures contra modelos reales.
El export no inicia lifespan ni llama APIs; no utiliza credenciales.
