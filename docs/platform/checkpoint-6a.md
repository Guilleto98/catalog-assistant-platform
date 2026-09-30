# Entrega Etapa 6A

## Persistencia y relaciones

SQLAlchemy 2.0 + Alembic + SQLite. Las rutas por defecto son application.db,
adk_sessions.db e intake.db dentro de `apps/agent/var`, ignoradas por Git y con
permisos privados. Catalog DB sigue separada. Las migraciones 0001 y 0002 crean
producto y protección append-only de auditoría.

Entidades: Organization, User, AuthSession, Conversation, Message,
MessageAttachmentReference, AgentRun, ToolExecution, UiEvent y AuditEvent.
Organization → User → Conversation → Message/AgentRun → ToolExecution; mensajes
referencian adjuntos y UI. Los IDs de Intake son referencias entre bases. Se
habilitan FK y se indexan propietario/organización, conversación, fechas, status,
runs y mensajes. El índice parcial de runs protege una ejecución activa por
conversación; mensaje tiene clave idempotente única.

## Identidad y contratos

Roles CLIENT_USER e INTERNAL_ADMIN. Password Argon2id; sesión opaca con hash de
token, cookie HttpOnly/SameSite=Lax/Secure configurable/Path=/ y TTL central.
Autorización por propietario y organización, auth FAIL CLOSED. Catalog demo
identity se inyecta server-side desde User.catalog_demo_user_id. CLI con getpass.

Conversation.adk_session_id relaciona IDs independientes. Runtime oficial
DatabaseSessionService, filtrado de pensamiento privado por append_event público,
sin MemoryService. POST /conversations/{id}/messages acepta clientMessageId y
registra USER → STARTED → ADK → ASSISTANT → COMPLETED, o FAILED seguro. Un retry
no ejecuta de nuevo; historial se lee sin modelo.

## Auditoría y admin

AgentRun persiste modelo/proveedor real, scope, tiempos, invocationId, requestId y
traceId. Tokens sólo desde metadata fiable; costo null. ToolExecution usa plugins
públicos y resúmenes pequeños. AuditEvent registra seguridad/negocio, incluyendo
accesos administrativos, attachments y drafts. UiEvent queda preparado para 6B.
Admin tiene lectura paginada de organizaciones, usuarios, conversaciones, runs y
eventos, con filtros. Errores y payloads se redactan; hashes/tokens/prompts completos
y pensamiento privado quedan fuera de la API y auditoría.

## Verificación

Suite final: **80 tests aprobados**, 7 integraciones/live omitidas por defecto.
Compilación Python y `git diff --check` sin errores. El smoke real de plataforma
se ejecutó aparte y pasó. ADK mantiene la advertencia experimental de declaraciones
JSON Schema ya conocida; no se modificaron dependencias para ocultarla.

Se probaron login correcto/incorrecto/desconocido, cookies, logout/revocación,
expiración, usuario/organización deshabilitados, ownership, admin audit, paginación,
archivo, idempotencia, proveedor fallido, scope fuera de dominio sin tools,
adjuntos cruzados rechazados, análisis/revisión autenticada y state de borrador,
mapeo de identidad catalog demo, triggers append-only y exclusión de thought.

Prueba crítica determinística con ADK persistente real: búsqueda BIFE_ANCHO,
cierre de servicios, reapertura y refinamiento CHINA conserva ambos criterios.
Otra conversación no hereda BIFE_ANCHO.

Smoke real OpenAI aprobado el 2026-09-30 con bases temporales:

1. Login, conversación y “Buscame bife ancho”: 5 resultados.
2. Cierre y nueva instancia de Application API, nuevo login, historial recuperado.
3. “Solo los de China”: 900001, BIFE_ANCHO + CHINA.
4. “Mostrame el primero”: get_article(900001).
5. Admin reconstruye tres runs COMPLETED y sus tools; la consulta genera audit.

El smoke usa `npm run agent:platform:smoke`, consume API de OpenAI y elimina sus
DBs temporales al terminar. No crea usuarios en la base oficial de la aplicación.

## Límites y siguiente etapa

Un cierre abrupto durante un run requiere reconciliación administrativa; no hay
replay automático. La demo usa SQLite y operaciones HTTP sin streaming. La
taxonomía/payload de UiEvent y los DTOs definitivos se congelarán en 6B. No hay
Angular, creación ni clonación. Scope sigue FAIL_OPEN y su baseline ~2.12s se
conserva. Las mutaciones requieren revisión explícita de seguridad de ese control.

Se mantienen deudas: rate limiting, antivirus, object storage, cifrado/backup,
retención/privacidad, SSO/MFA/password reset, DB productiva y restricción Swagger.
catalogDemoUserId es temporal y no debe compartirse entre clientes durante demo.

Recomendación 6B: congelar DTOs públicos, definir eventos versionados y validar
reconstrucción del historial con cards sin volver a invocar el modelo.
