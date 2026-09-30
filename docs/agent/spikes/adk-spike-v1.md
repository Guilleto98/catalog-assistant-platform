# ADK Spike V1 — Etapa 4

## Baseline

- Fecha: 2026-09-29
- Python objetivo: 3.12
- Google ADK: 2.10.0
- Proveedor: OpenAI mediante el conector LiteLLM de ADK Python
- Modelo configurable, default: `openai/gpt-6-luna`
- Runtime: un `root_agent`, sin subagentes
- Session: in-memory de ADK
- State: `ToolContext.state`, aislado por sesión

## Arquitectura validada

```text
ADK root agent
  -> Python function tool
  -> CatalogApiClient (httpx async + timeout)
  -> Catalog API HTTP
```

No hay imports de NestJS, Prisma o SQLite desde Python. El cliente normaliza claves
a camelCase y clasifica errores sin exponer stack traces.

| Tool | Endpoint | State escrito sólo al éxito |
| --- | --- | --- |
| `search_articles` | `POST /api/v1/articles/search` | `current_search`, `last_search_codes` |
| `get_article` | `GET /api/v1/articles/{codigo}` | `last_article_code` |
| `compare_articles` | `POST /api/v1/articles/compare` | `last_comparison_codes` |

`current_search` guarda el request completo. La instruction conserva criterios no
afectados, reemplaza el filtro del mismo field y reinicia la página al refinar. Los
ordinales se resuelven contra `last_search_codes`; sin esa lista se pide aclaración.

## Verificación automática

Los unit tests cubren requests search/detail/compare, normalización, validación,
not-found, timeout, API no disponible, argumentos de tools, resultados y state. La
integración opcional usa el benchmark BIFE_ANCHO + CHINA = `900001`.

Resultados del 2026-09-29:

- Agent unit: 10/10 pass.
- Agent integration contra API real: 1/1 pass; devolvió `900001`.
- Catalog API unit: 5/5 pass.
- Catalog API e2e: 17/17 pass.
- Catalog API build y lint: pass.
- Import/compile: pass con Python 3.12.14 y ADK 2.10.0.
- ADK Web: inició correctamente en un puerto local, cargó storage/session
  in-memory y se cerró de forma controlada.

## Smoke scenarios

| Escenario | Esperado | Resultado real |
| --- | --- | --- |
| A — search China | 1 search; BIFE_ANCHO + CHINA | PASS: `900001`, una llamada y argumentos exactos |
| B — detail 900001 | 1 detail con `900001` | PASS: una llamada a detail |
| C — compare 3 | 1 compare con tres códigos | PASS: una llamada; 15 fields diferentes y 6 iguales |
| D — refinement | conserva BIFE_ANCHO y agrega CHINA | PASS: conserva corte; resultado `900001` |
| E — replace | reemplaza CHINA por BRASIL | PASS: no conserva CHINA; resultado `900002` |
| F — ordinal | detalle del segundo resultado | PASS: resolvió segundo a `900004` |
| G — ambiguity | aclaración, 0 tools | PASS: pidió contexto, cero llamadas |
| H — similarity | capacidad no habilitada, 0 tools | PASS: explicó límite, cero llamadas |

La suite se ejecuta con `npm run agent:smoke` y registra tool, argumentos,
respuesta resumida, respuesta final y state por turno.

### Baseline OpenAI — primera ejecución real

Con `openai/gpt-6-luna`, detalle, comparación, ambigüedad y capability gating
seleccionaron correctamente la tool o ausencia de tool esperada. Search seleccionó
`search_articles` una sola vez, pero construyó fields abreviados o traducidos como
`cut`, `corte`, `destination`, `destino`, `mercado` y `temperature`. La API rechazó
correctamente esos requests con `INVALID_FILTER_FIELD`, por lo que refinement,
replace y ordinal no pudieron continuar y el state permaneció vacío.

Cambio mínimo aplicado antes de reevaluar: la docstring de `search_articles` ahora
enumera los paths exactos más comunes y ejemplos de enums uppercase. No se agregó
router, traducción determinística ni fallback.

### Resultado de la reevaluación

Después del cambio de docstring, los ocho escenarios pasaron con
`openai/gpt-6-luna`. Cada operación normal usó una sola tool. Refinement y replace
produjeron el state esperado; el ordinal resolvió el segundo código; ambigüedad y
similitud no realizaron llamadas. No fue necesario modificar la instruction ni la
representación del state.

## Límites y recomendación

- El estado es efímero y desaparece al recrear la sesión.
- La suite es un smoke real y puede variar estadísticamente; no se agregó routing
  por palabras clave.
- No hay fallback que fabrique datos si falla la Catalog API.
- Similitud, endpoint de chat y Angular permanecen fuera de alcance.

Repetir la suite varias veces antes de ampliar el alcance para medir estabilidad y
coste. Si falla un escenario, ajustar primero docstrings, instruction o state.
