# Etapa 5A.2 — Hardening & Hygiene Checkpoint

## Resumen ejecutivo

No se detectaron credenciales versionadas ni vulnerabilidades críticas/altas en
el alcance revisado. `.env`, attachments, SQLite de intake y SQLite de ADK están
ignorados. Se aplicaron correcciones pequeñas: firma mínima de uploads, permisos
privados de runtime, schemas OpenAPI de respuesta y reemplazo del TestClient
deprecado. Las regresiones de ownership, path traversal, prompt injection,
persistencia y scope permanecen cubiertas.

El riesgo operativo principal no es de código: el repositorio tiene una
reestructuración Git todavía sin consolidar. El status inicial muestra muchos
archivos legacy eliminados y los nuevos directorios `apps/` y `docs/` como
untracked. No se modificó ni limpió ese estado; debe revisarse cuidadosamente al
preparar el futuro commit.

## Estado inicial de Git

- Root: raíz de este repositorio.
- Existían modificaciones previas en `.gitignore`, `README.md` y `package.json`.
- El layout legacy aparecía con múltiples eliminaciones tracked.
- `apps/`, documentación nueva y otros artefactos del proyecto aparecían
  untracked.
- `.env`, `.venv`, caches y runtime del agente aparecían ignored.

No se ejecutaron `reset`, `clean`, checkout destructivo ni reescritura de
historial.

## Hallazgos corregidos

### HYG-001 — SQLite de ADK sin regla específica

- Severidad: Low.
- Ubicación: `.gitignore`, líneas 11–12.
- Evidencia: existía `apps/agent/solvo_client_agent/.adk/session.db`; sólo el intake
  `apps/agent/var/` tenía exclusión específica.
- Impacto: una futura selección amplia de archivos podía incorporar estado local
  de conversaciones.
- Fix: se agregó `apps/agent/solvo_client_agent/.adk/` y se aplican permisos `0700/0600`
  al runtime.
- Estado: corregido.

### SEC-001 — Upload validado por extensión/MIME, sin firma mínima

- Severidad: Medium.
- Ubicación: `apps/agent/solvo_client_agent/services/attachments.py`, método `upload` y
  `_validate_signature`.
- Evidencia: antes del checkpoint la decisión de tipo usaba extensión + MIME; el
  parser detectaba formatos inválidos recién durante el procesamiento.
- Impacto: contenido completamente distinto podía persistirse temporalmente bajo
  una extensión permitida.
- Fix: comprobación de magic bytes/contenedor para PDF, XLSX, WAV, WebM, MP3 y
  MP4/M4A antes de escribir; error estable `ATTACHMENT_CONTENT_MISMATCH`.
- Mitigación futura: antivirus/quarantine antes de producción.
- Estado: corregido y cubierto por regresión.

### API-001 — Respuestas de intake poco descriptivas en OpenAPI

- Severidad: Low.
- Ubicación: `apps/agent/solvo_client_agent/api/app.py`, rutas de attachments/drafts;
  `apps/agent/solvo_client_agent/api/schemas.py`.
- Evidencia: los handlers devolvían diccionarios sin `response_model`.
- Impacto: Swagger no documentaba de forma precisa contratos exitosos y errores.
- Fix: schemas explícitos para attachment, transcripción, análisis, drafts,
  estado y errores; test sobre multipart y respuestas.
- Estado: corregido.

### TEST-001 — Deprecación de TestClient

- Severidad: Low.
- Origen exacto: `fastapi.testclient` sobre FastAPI `0.141.1`, Starlette `1.7.0`
  y httpx `0.28.1` emitía `StarletteDeprecationWarning` recomendando `httpx2`.
- Impacto: ninguno en runtime; deuda de compatibilidad futura en tests.
- Fix: reemplazo compatible por `httpx.AsyncClient` + `ASGITransport`, sin
  upgrades ni pins nuevos.
- Estado: corregido; suite sin warning.

## Controles confirmados

- Secretos: ninguna credencial real encontrada en archivos tracked o fuentes
  no ignoradas. No se imprimieron valores del `.env`.
- `.env.example`: sólo nombres y defaults no sensibles usados por el código.
- Storage: `apps/agent/var/attachments`, ignorado; directorio `0700`, archivos
  `0600`, IDs aleatorios y path traversal bloqueado.
- SQLite intake: `apps/agent/var/intake.db`, ignorado y `0600`.
- SQLite ADK: `apps/agent/solvo_client_agent/.adk/session.db`, ignorado y endurecido al
  iniciar el agente.
- Derivados: transcripción, texto PDF/XLSX y respuestas de extracción no se
  escriben como archivos intermedios. No se detectaron `.tmp`/`.part` huérfanos.
- Cleanup: cargas parciales se eliminan; documentos administrados que fallan al
  procesarse permanecen intencionalmente con estado `ERROR`.
- Aislamiento: attachments y drafts validan `conversation_id`; acceso cruzado
  devuelve `ACCESS_DENIED`.
- Persistencia: un draft continúa accesible después de reinstanciar el
  repositorio sobre el mismo SQLite.
- Estado ADK: guarda identificadores, criterios y auditoría; no binarios ni
  contenido documental completo.
- Scope: cada `invocation_id` nuevo se reclasifica; una decisión anterior no
  bloquea el siguiente turno.
- Errores: responses controladas no incluyen paths, stack traces, errores OpenAI
  completos, API keys ni ubicación SQLite.

## Current Technical Debt

1. El scope semántico agrega un baseline local promedio de ~2,12 s por turno.
   Optimización futura de UX; no bloquea 5B.
2. `FAIL_OPEN` del scope **MUST REVISIT BEFORE MUTATIONS**.
3. `X-Demo-Conversation-Id` no es autenticación de producción.
4. Faltan controles de producción en el edge: body limit previo al parser
   multipart, rate limiting, trusted hosts/proxy y restricción de Swagger.
5. Faltan antivirus/quarantine, object storage, cifrado, retención y jobs
   asíncronos para archivos reales.
6. La reestructuración Git pendiente requiere revisión manual antes de crear un
   commit para no incluir eliminaciones legacy involuntarias.
7. Google ADK 2.10 emite `FeatureName.JSON_SCHEMA_FOR_FUNC_DECL is enabled`
   durante el smoke real. Es un warning interno experimental, no un fallo
   funcional; monitorear en futuras versiones sin upgrade preventivo.

## Riesgos no confirmados

- La configuración de reverse proxy, TLS, límites de body y seguridad perimetral
  no existe en este spike local; deberá verificarse al definir deployment.
- No se hizo un upgrade de dependencias. Las versiones instaladas relevantes
  para uploads son FastAPI 0.141.1, Starlette 1.7.0, httpx 0.28.1 y
  python-multipart 0.0.32.

## Verificación final

- Agent determinístico: 58 passed.
- Agent + Catalog API integration: 1 passed.
- Domain scope con provider real: 5 passed.
- Catalog API unit: 5 passed.
- Catalog API E2E: 17 passed.
- Catalog API lint y build: aprobados.
- Smoke conversacional: búsqueda, detalle, comparación, refinamiento,
  reemplazo, ordinal, ambigüedad y capability no soportada aprobados.
- Scope smoke: `IN_SCOPE`, `ADJACENT_ALLOWED`, `OUT_OF_SCOPE`, `AMBIGUOUS` e
  internal prompt protection aprobados.
- Intake smoke: extracción XLSX, campos normalizados y provenance aprobados.
- `git diff --check` y compilación Python: aprobados.
