# Tool Catalog V1

Las tools son operaciones del dominio, no endpoints HTTP. Cada una valida estructura básica, delega la validación autoritativa a la Catalog API, normaliza la respuesta y devuelve `ToolResult<T>`. No contienen razonamiento LLM.

## Matriz API

| Tool | API operation | Supported |
| --- | --- | --- |
| `get_filterable_fields` | `GET /api/v1/metadata/filterable-fields` | Sí |
| `search_articles` | `POST /api/v1/articles/search` | Sí |
| `get_article` | `GET /api/v1/articles/{codigo}` | Sí |
| `compare_articles` | `POST /api/v1/articles/compare` | Sí |
| `find_similar_articles` | `POST /api/v1/articles/similar` | Sí |
| `get_technical_sheet` | `GET /api/v1/articles/{codigo}/technical-sheet` o `GET /api/v1/technical-sheets/{fichaId}` | Sí |
| `save_filter` | `POST /api/v1/saved-filters` | Sí |
| `list_saved_filters` | `GET /api/v1/saved-filters` | Sí |
| `get_saved_filter` | `GET /api/v1/saved-filters/{id}` | Sí |
| `execute_saved_filter` | `POST /api/v1/saved-filters/{id}/execute` | Sí |
| `delete_saved_filter` | `DELETE /api/v1/saved-filters/{id}` | Sí |

No se exponen health, reset, seed, Swagger, Prisma, Docker ni endpoints internos al modelo.

## get_filterable_fields

> Discover the filterable catalog fields, their types, supported operators, nullability, units, and allowed values. Use this only when a field or value mapping needs validation or discovery; do not call it automatically before every search.

- **Use when:** falta seguridad sobre path, tipo, operador o enum.
- **Do not use when:** los criterios ya son inequívocos y conocidos.
- **Visible input:** objeto vacío.
- **Security:** no acepta SQL, paths solicitados ni expresiones.

## search_articles

> Search the catalog for articles matching structured field criteria. Use this when the user wants to find articles by characteristics. Do not use it when the user wants alternatives based on similarity to a reference article.

- **Use when:** el usuario describe corte, mercado, temperatura, vida útil, ausencia de códigos u otros atributos filtrables.
- **Do not use when:** pide detalle, comparación, similarity o ficha.
- **Parameter guidance:** `field` must be a filterable metadata path; `operator` must be supported for that field; `value` must match its type and is omitted for default `is_null` behavior.

## get_article

> Get the current complete catalog record for one known article code. Use this for article detail or when a current field value must be verified. Do not construct URLs or answer authoritative article data from conversation memory.

- **Use when:** código explícito o referencia resuelta; dato actual requerido.
- **Do not use when:** un summary de búsqueda ya satisface la pregunta o se buscan alternativas.

## compare_articles

> Compare the structured attributes of two to ten unique known articles. Use this when the user wants to understand differences between specific articles. Do not use it to discover alternative articles.

- **Use when:** existen 2–10 códigos resueltos.
- **Do not use when:** se busca similitud o faltan referencias.
- **Parameter guidance:** `codes` preserves the user-visible order and contains no duplicates.

## find_similar_articles

> Find articles similar to exactly one reference article or one feature set. Use `required` only for criteria the user explicitly indicates are mandatory. Do not infer eligibility yourself; preserve the eligibility and evaluation statuses returned by this tool.

- **Use when:** se buscan alternativas a una referencia.
- **Do not use when:** solo se describen atributos deseados o se comparan artículos conocidos.
- **Parameter guidance:** provide `referenceCode` or `features`, never both. `required` contains criteria every eligible candidate must satisfy and only when wording clearly makes them mandatory.

## get_technical_sheet

> Get the current metadata-only technical sheet by article code or technical-sheet ID. Provide exactly one identifier. This tool does not return a PDF, sections, microbiology, ingredients, or any content not supported by the Catalog API.

- **Use when:** se pide la ficha asociada o una ficha por ID.
- **Do not use when:** se espera descargar o analizar un PDF inexistente.
- **Design:** una tool semántica con dos identificadores opcionales y validación exactly-one; es más simple para el usuario que exponer dos tools. Si el schema del runtime ADK no expresa bien esta restricción, el adaptador la valida antes de HTTP.

## save_filter

> Save a structured catalog search for the current application user. Save criteria, not results. Use the structured current search when the user says “save this search”. User identity is injected by the backend and is never a model argument.

- **Use when:** existe una búsqueda estructurada válida y un nombre.
- **Do not use when:** no existe búsqueda ni criterios en el mismo turno.
- **Write:** crea un recurso personal; no se implementa idempotencia compleja en V1.

## list_saved_filters

> List saved filters owned by the current application user. Use it to show saved searches or resolve a user-provided filter name to an ID. User identity is implicit.

- **Visible input:** objeto vacío.
- **Do not use when:** ya existe un ID inequívoco en contexto.

## get_saved_filter

> Get one saved filter owned by the current application user by its resolved ID. Use it to inspect saved criteria, not to execute them.

- **Parameter guidance:** `savedFilterId` must come from state or a resolved list result, never be invented.

## execute_saved_filter

> Execute one saved filter by its resolved ID against current catalog data. Do not return historical conversation results as if they were current.

- **Use when:** el usuario quiere volver a correr un filtro.
- **Resolution by name:** `list_saved_filters` → exact/unique name → `execute_saved_filter`.

## delete_saved_filter

> Delete one saved filter owned by the current application user by its resolved ID. Use only for an explicit, unambiguous delete intent; ask for clarification when the target is ambiguous.

- **Confirmation decision V1:** una orden inequívoca como “Borrá el filtro China congelados” se ejecuta sin confirmación adicional. “Borrá ese” requiere aclaración si el antecedente no es único.
- **Resolution by name:** `list_saved_filters` → exact/unique name → `delete_saved_filter`.
- **Risk:** escritura personal de bajo riesgo; no sienta precedente para mutaciones de artículos.

## Capacidades fuera del catálogo

Ranking adicional, grouping, alta o edición de artículos, bulk mutation, PDFs reales, RAG y generación de fichas no existen en la API y no se simulan en el agente.
