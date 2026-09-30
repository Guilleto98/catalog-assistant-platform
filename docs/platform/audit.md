# Auditoría observable — Etapa 6A

AuditEvent registra historia durable de negocio/seguridad. Los logs registran
diagnóstico operativo y no sustituyen esa historia. Auditoría es append-only:
no hay API de update/delete y SQLite bloquea ambas operaciones mediante triggers
de la migración `0002_append_only_audit`.

AgentRun vincula conversación, mensaje USER, respuesta ASSISTANT, proveedor/modelo
reales de configuración, estado, requestId, traceId, invocationId, scope y tiempos.
Los tokens se guardan sólo cuando ADK devuelve usage; costo queda null.

ToolExecution usa el plugin público de ADK: before_tool, after_tool y
on_tool_error. Registra orden, duración, estado y argumentos redactados. Los
resultados se resumen: códigos/conteos, paginación o IDs/estado de borradores.
No se duplican documentos ni catálogos completos. UiEvent tiene schemaVersion y
payload preparado para 6B; esta etapa no genera automáticamente cards de UI.

Se registran login exitoso/fallido, logout, conversación creada/archivada,
mensaje USER, inicio/fin/fallo de run, herramientas, uploads, creación/revisión/
confirmación de borradores y consultas administrativas a conversaciones y runs.
Cada request tiene X-Request-Id; se conserva un ID entrante sólo si cumple el
formato alfanumérico/guion/underscore de hasta 64 caracteres.

Nunca se almacena en auditoría: contraseñas, cookies/tokens raw, credenciales,
prompts de sistema completos, bytes de archivos, texto documental raw o pensamiento
privado. Se redactan claves sensibles, patrones de credenciales y Bearer tokens,
con límites de tamaño/profundidad. La persistencia pública append_event de ADK
filtra partes thought y thought_signature antes de guardarlas. La conversación
de producto almacena únicamente el texto final observable del asistente.

El namespace `/admin` requiere INTERNAL_ADMIN:

- organizations/users/conversations/runs/audit-events: lectura paginada;
- conversation detail: organización, usuario, mensajes, referencias, runs y tools;
- run detail: mensajes vinculados, scope, tiempos y herramientas.

Se ofrecen filtros por organización/usuario/conversación, estado, herramienta,
scope, error y fechas según el recurso. Los campos password_hash/token_hash nunca
se serializan. Las respuestas de fallo no muestran errores raw del proveedor,
paths de SQLite ni stack traces.

Los futuros eventos ARTICLE_CREATION_PREVIEWED/CONFIRMED/CREATED y ARTICLE_CLONED
se diseñarán con las mutaciones. El scope permanece FAIL_OPEN:
**MUTATIONS MUST NOT BE ENABLED WHILE THIS CONTROL REMAINS FAIL_OPEN WITHOUT
EXPLICIT SECURITY REVIEW**. El runtime incluye bloqueo para tools de mutación
conocidas. Auth/autorización permanecen FAIL CLOSED.

Deuda antes de producción: rate limiting en edge/login, antivirus, object storage,
cifrado y backup, retención de conversaciones/adjuntos/auditoría, privacidad y
borrado, SSO/MFA/password reset, base productiva, restricciones Swagger. Se conserva
el baseline de scope ~2.12 s; no se optimizó en esta etapa.
