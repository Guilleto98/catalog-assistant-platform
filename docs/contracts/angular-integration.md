# Integración Angular futura — sin implementar Etapa 6C

Base URL de Application API: `http://127.0.0.1:3100/api/v1`.
Catalog API `:3000/api/v1` es otra aplicación: Angular no la consulta directamente
ni carga OpenAI/Gemini keys. OpenAPI exportado es fuente para tipos/clientes TS.

## Sesión y navegación

1. POST `/auth/login` con `{email,password}` y `withCredentials:true`.
2. GET `/auth/me` al cargar la app; muestra email, rol y organización.
3. GET `/conversations?page=1&pageSize=20` carga sidebar ya ordenado por actividad.
4. POST `/conversations` crea conversación; guardar su id y metadata.
5. GET `/conversations/{id}` + GET `/conversations/{id}/messages` reconstruyen
   el historial; mensajes ASC y paginación, sin LLM/ADK/Catalog.
6. POST `/auth/logout` revoca cookie; no guardar JWT ni credenciales en localStorage.

Usar `withCredentials:true` en HttpClient (o fetch `credentials:'include'`) en
**todas** las peticiones autenticadas. FRONTEND_ORIGIN debe coincidir exactamente
con el origen Angular, default `http://localhost:4200`; CORS no usa wildcard con
cookies. Cookie HttpOnly/SameSite=Lax; producción HTTPS requiere Secure. Mantener
hostname consistente (localhost y 127.0.0.1 no son intercambiables para cookies).
Para desarrollo Angular localhost usar Application API `http://localhost:3100`.

## Enviar mensajes

Crear UUID clientMessageId una sola vez por intención del usuario. POST
`/conversations/{id}/messages`:
`{clientMessageId,text:'Buscame bife ancho para China.',attachmentIds:[]}`.
Mostrar “procesando” mientras se espera. No SSE/WebSockets/token streaming en V1.
Al resolver, usar los IDs retornados para deduplicar y añadir userMessage y
assistantMessage. Renderizar texto como texto y uiEvents mediante switch(type).
Retry de la misma petición conserva el mismo UUID y contenido. Cambiar contenido
con ese UUID produce 409. Un run FAILED no se reejecuta automáticamente;
un nuevo intento explícito del usuario crea otro UUID. STARTED puede aparecer en
retry concurrente: consultar historial o esperar respuesta original.

ARCHIVED es readable; bloquear composer y manejar CONVERSATION_ARCHIVED si otro
cliente archivó mientras se enviaba. No implementar restore inexistente.

## Adjuntos y revisión

Upload multipart con campo `file` a `/conversations/{id}/attachments`.
No fijar manualmente Content-Type del multipart: navegador agrega boundary.
Mostrar AttachmentDto.filename original, type/status; nunca intentar interpretar
un storage path. GET `/attachments/{attachmentId}` dentro de esa conversación
consulta estado. Procesamiento actual es síncrono en POST, pero otro cliente puede
consultar PROCESSING; polling es suficiente, sin sockets.

Audio: POST `/transcribe`, luego usar AttachmentDto.transcription. Documento PDF/
XLSX: POST `/analyze`, mostrar RequestDraftPayload para revisión. Confirmar/corregir/
rechazar campo mediante `/drafts/{draftId}/review`; nunca editar artículo del catálogo.
Sólo adjuntos READY pueden enviarse con mensaje. `text:null` + attachmentIds permite
audio-only/document-only. Otros documentos requieren análisis antes de envío.
Análisis/revisión generan SYSTEM_EVENT y nuevos UiEvents persistidos; recargar
messages después de estas operaciones para incorporar eventos. No convertirlos
en un segundo assistant ni reescribir tarjetas antiguas.

## Renderer y errores

Renderizar contratos de [`ui-events-v1.md`](ui-events-v1.md); historial persiste
exactamente lo visto, incluso sin providers disponibles. sequence ordena eventos
por mensaje. Tipo/schemaVersion desconocido: mostrar fallback seguro; no inventar
conversión a V1 ni reprocesar conversación. Similarity separa aptos/no aptos según
eligibility, no umbral arbitrario de score. Ficha sin documento no ofrece PDF.

Paginación unificada `{items,page,pageSize,total}`, default20/máximo100.
Mensajes entre páginas mantienen orden cronológico; append páginas posteriores
sin invertir cada página. Sidebar fecha descendente. Localizar timestamps UTC
en el navegador, conservando valor original para auditoría.

Error HTTP: leer `error.code`, `error.message`, `error.requestId` y correlacionar
con header. 401 vuelve a login; 403 permisos/estado; 404 recurso no disponible;
409 conflicto/mensaje/adjunto; 422 validación; 5xx operación no completada.
No mostrar stacktrace ni prompts. No reenviar automáticamente una operación que
pudo persistir User Message/run. ERROR UiEvent se presenta dentro del chat y no
sustituye error HTTP. RATE_LIMITED y PROVIDER_UNAVAILABLE son reservas, no promesas.

## Administración

Sólo INTERNAL_ADMIN ve navegación de auditoría. La restricción frontend es UX;
backend vuelve a autorizar cada request. `/admin` devuelve DTOs diferentes con
scope, provider/model, timing y argumentos seguros; nunca pasarlos al renderer
del cliente. Leer una conversación administrativa genera AuditEvent. No hay
consultas nuevas al modelo para construir vistas administrativas.

## Validación antes de 6C

Generar tipos desde `application-api-v1.openapi.json`; no copiar modelos ORM.
Probar login/logout/expiración, ownership entre dos usuarios, sidebar, retries,
historial offline de providers, archivo READY, draft correction e INELIGIBLE.
Mantener datos/tablas separados de narrativa y tratar nombres/documentos como
texto no confiable. No iniciar creación/clonado/RAG en esta etapa.
