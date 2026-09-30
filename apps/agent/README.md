# Agente de catálogo — backend y Application API

La Etapa 6B formaliza `/api/v1`, DTOs públicos y UiEvents persistidos para el futuro
Angular. Ver [contratos](../../docs/contracts/application-api-v1.md),
[integración Angular](../../docs/contracts/angular-integration.md) y
[checkpoint 6B](../../docs/platform/checkpoint-6b.md). No implementa Angular.

La Etapa 6A agrega la Application API autenticada y persistente. El comando
canónico es `npm run agent:api` en puerto 3100; `agent:intake` queda como alias.
Ver `docs/platform/identity.md` para crear organización/usuarios con la CLI,
login con cookies y mapeo de identidad del catálogo. Las migraciones Alembic se
aplican al iniciar; Application DB, Intake DB y ADK DB son independientes.

Los endpoints legacy de intake requieren `LEGACY_INTAKE_ENABLED=true` para
pruebas internas. El producto usa `/conversations/{id}/attachments` y
`/conversations/{id}/drafts` con la sesión autenticada.

Primer agente funcional del monorepo. La Etapa 4 valida un único agente raíz de
Google ADK que conversa en español y consulta la Catalog API real. La Etapa 5A
agrega carga de audio, PDF y XLSX, transcripción, extracción estructurada y un
borrador auditable con revisión humana.
La Etapa 5B completa la consulta con similitud, fichas técnicas, metadatos,
filtros guardados y el flujo determinístico borrador → similitud.

## Mapa del código

- `solvo_client_agent/agent.py`, `tools/` y `state/`: agente ADK, herramientas y contexto conversacional.
- `clients/` y `scope/`: integración con Catalog API y guardia de dominio.
- `domain/`, `services/`, `storage/` y `repositories/`: modelos y flujo de intake de adjuntos/borradores.
- `platform/`: identidad, autorización, persistencia de conversaciones, auditoría y lógica de aplicación.
- `platform/routes.py`: rutas autenticadas de producto y administración; delega en `platform/`.
- `api/app.py`: composición/lifespan de FastAPI, middleware y rutas legacy de intake.
- `migrations/` y `tests/`: cambios de esquema y pruebas Python.

La superficie legacy de intake vive en `api/app.py`; la Application API autenticada
se define en `platform/routes.py`. Se mantienen separadas por ser rutas con modelos
de autenticación distintos. Para cambios futuros, dividir `platform/routes.py` por
dominio cuando el tamaño dificulte localizar o revisar las rutas.

## Requisitos e instalación

- Python 3.12 (administrado por `uv`)
- `uv`
- Catalog API disponible en `http://localhost:3000/api/v1`
- Una `OPENAI_API_KEY` creada en OpenAI Platform

Desde la raíz del monorepo:

```bash
npm run agent:install
cp apps/agent/.env.example apps/agent/.env
```

Complete `OPENAI_API_KEY` en `.env`; ese archivo está ignorado por Git. No coloque
la clave en `.env.example`. Google ADK Python se conecta a OpenAI mediante LiteLLM.
El modelo se configura una sola vez con `AGENT_MODEL`; el predeterminado es
`openai/gpt-6-luna`. La URL y timeout se controlan con `CATALOG_API_BASE_URL` y
`CATALOG_API_TIMEOUT_SECONDS`.

## Ejecutar

En terminales separadas:

```bash
npm run api:dev
npm run agent:dev
npm run agent:intake
```

Seleccione `solvo_client_agent` en el playground. Para la conversación por terminal:

```bash
npm run agent:run
```

La API de intake queda en `http://127.0.0.1:3100` y su Swagger en `/docs`. Los
adjuntos y borradores se persisten localmente en `apps/agent/var`; ADK conserva
solamente sus IDs y el contexto de búsqueda.

Las variables soportadas están enumeradas en `.env.example`: credencial OpenAI,
modelo principal, conexión a Catalog API, modelos de transcripción/extracción y
scope, límites de archivos, MIME/extensiones, rutas de storage/SQLite y límites
de parsing. `.env` y todos los datos runtime están excluidos de Git.

## Control semántico de dominio

Antes de cada turno, un `before_model_callback` clasifica semánticamente el
mensaje como `IN_SCOPE`, `ADJACENT_ALLOWED`, `OUT_OF_SCOPE` o `AMBIGUOUS`. Usa el
mensaje actual, hasta cuatro fragmentos recientes y un resumen pequeño del
estado; no recibe documentos completos. Las dos primeras decisiones continúan
al agente. Las dos últimas lo omiten y devuelven una redirección o aclaración
breve. Las solicitudes de configuración interna también se interceptan.

```dotenv
DOMAIN_SCOPE_ENABLED=true
DOMAIN_SCOPE_MODEL=gpt-4.1-mini
DOMAIN_SCOPE_TIMEOUT_SECONDS=8
```

Si el clasificador falla, la versión actual continúa en modo `FAIL_OPEN` y lo
registra, ya que todavía no hay mutaciones críticas. La decisión, razón, latencia
y ejecución/omisión del agente aparecen como `domain_scope_*` en el estado de la
sesión y en logs. Una solicitud mixta continúa sólo para atender la parte válida.
El dataset está en `docs/evals/domain-scope-v1.md` y el diseño detallado en
`docs/agent/domain-scope.md`.

## Herramientas habilitadas

- `search_articles`: `POST /articles/search`
- `get_article`: `GET /articles/{codigo}`
- `compare_articles`: `POST /articles/compare`
- `find_similar_articles`: `POST /articles/similar`
- `get_technical_sheet`: `GET /articles/{codigo}/technical-sheet` o
  `GET /technical-sheets/{fichaId}`
- `get_filterable_fields`: `GET /metadata/filterable-fields`
- `save_filter`, `list_saved_filters`, `get_saved_filter`,
  `execute_saved_filter`, `delete_saved_filter`: `/saved-filters`
- `get_request_draft`: lectura del borrador asociado a la sesión
- `update_request_draft`: confirmación, corrección o rechazo de un campo

El cliente usa `httpx.AsyncClient`, timeout explícito y resultados JSON limpios.
Clasifica validación, artículo inexistente, API no disponible, timeout y respuesta
upstream inesperada. El modelo nunca recibe URLs, credenciales ni `userId`.

## Probar adjuntos

Todos los endpoints requieren `X-Demo-Conversation-Id`:

```bash
curl -X POST http://127.0.0.1:3100/attachments \
  -H 'X-Demo-Conversation-Id: prueba-1' \
  -F 'file=@pedido.pdf'
```

Con el `id` devuelto, use `POST /attachments/{id}/analyze` para PDF/XLSX o
`POST /attachments/{id}/transcribe` para audio. El análisis devuelve un
`ArticleRequestDraft`; nunca crea un artículo.

## Tests

```bash
npm run agent:test
npm run agent:test:integration  # con Catalog API levantada
npm run agent:smoke             # con Catalog API + OPENAI_API_KEY
npm run agent:scope:smoke       # 4 clasificaciones reales, consume API
npm run agent:intake:smoke      # extracción real representativa, consume API
```

Los unit tests no usan un LLM real. La selección conversacional se inspecciona en
el trace del playground y se registra en `docs/agent/spikes/adk-spike-v1.md`.

## Fuera de alcance

No están implementados creación o clonación de artículos, OCR, antivirus,
procesamiento asíncrono, object storage, RAG, MCP, subagentes, `/chat` propio ni
Angular.

## Current Technical Debt

- El scope semántico agrega aproximadamente 2,12 s promedio por turno en el
  baseline local; la optimización de UX queda para una etapa posterior.
- `FAIL_OPEN` debe revisarse obligatoriamente antes de habilitar mutaciones.
- Las rutas de producto verifican sesión, propietario y organización; el header
  `X-Demo-Conversation-Id` sólo queda en la ruta legacy deshabilitada por defecto.
- `catalog_demo_user_id` es un puente temporal al catálogo; asignar el mismo ID
  a dos usuarios compartiría filtros allí. Debe reemplazarse con auth real.
- Un cierre abrupto durante un run requiere reconciliación administrativa; no se
  repiten herramientas automáticamente.
- Antes de producción faltan límites en el edge, rate limiting, antivirus,
  object storage, cifrado/retención y procesamiento asíncrono.
- Swagger está expuesto deliberadamente para desarrollo local; deberá
  restringirse o deshabilitarse en una publicación pública.
- Google ADK 2.10 emite una advertencia no bloqueante por su soporte experimental
  de JSON Schema para declaraciones de tools durante el smoke real; no se
  aplicaron hacks ni upgrades para ocultarla.
