# Contratos de tools V1

## Convenciones

- El schema visible al modelo usa `camelCase`.
- `CatalogApiClient` serializa a `snake_case` (`pageSize` → `page_size`, `referenceCode` → `reference_code`) y normaliza respuestas en sentido inverso.
- Los contratos nunca exponen URL base, headers, `userId` ni `conversationId`.
- Los outputs son `ToolResult<T>`; no se retorna `AxiosResponse`, stack trace ni respuesta HTTP cruda.
- La tool valida forma, rangos simples y exclusiones mutuas. La API conserva la validación autoritativa de fields, enums y reglas del catálogo.

## Tipos compartidos

```ts
type FilterOperator =
  | 'eq' | 'neq' | 'in' | 'contains'
  | 'gte' | 'lte' | 'between' | 'is_null'

interface SearchFilter {
  field: string
  operator: FilterOperator
  value?: unknown
}

interface SearchSort {
  field: string
  direction: 'asc' | 'desc'
}

interface SearchSpec {
  filters: SearchFilter[]
  sort: SearchSort[]
  page: number
  pageSize: number
}
```

`is_null` permite omitir `value`; la API también admite boolean para distinguir null (`true`/omitido) de no-null (`false`). `in` exige un array no vacío y `between` exactamente dos valores.

## 1. get_filterable_fields

- **HTTP:** `GET /api/v1/metadata/filterable-fields`
- **Visible input:** `{}`
- **Injected context:** ninguno para la API; `conversationId` solo para trazabilidad futura.
- **Input validation:** rechazar propiedades desconocidas.
- **Normalized output:**

```ts
interface FilterableField {
  path: string
  type: 'string' | 'number' | 'boolean' | 'date'
  nullable: boolean
  unit: string | null
  operators: FilterOperator[]
  allowedValues?: Array<string | number | boolean>
}
interface GetFilterableFieldsResult { fields: FilterableField[] }
```

- **Observed mapping:** API `allowed_values` → internal `allowedValues`.
- **Errors:** upstream, timeout, unknown; no domain 404 esperado.
- **State:** no lee ni escribe estado autoritativo; el resultado puede usarse durante el turno, no necesita persistirse.
- **Security:** no acepta field path del modelo ni expresiones ejecutables.

## 2. search_articles

- **HTTP:** `POST /api/v1/articles/search` (respuesta HTTP 201 actual).
- **Visible input:**

```ts
interface SearchArticlesInput {
  filters?: SearchFilter[]
  sort?: SearchSort[]
  page?: number       // integer >= 1
  pageSize?: number   // integer 1..50
}
```

- **HTTP mapping:** `pageSize` → `page_size`; el resto conserva forma.
- **Basic validation:** arrays reales; operador incluido en union; page/pageSize enteros en rango; sin expresiones o propiedades desconocidas. Metadata/API valida compatibilidad field/operator/value.
- **Normalized output:**

```ts
interface ArticleSummary {
  code: string
  name: string
  cut: string | null
  species: string | null
  market: string | null
  destinationCountry: string | null
  temperature: string | null
  presentation: string | null
  primaryPackaging: string | null
  outerPackaging: string | null
  weightType: string | null
  averageWeightKg: number | null
  active: boolean
  technicalSheetId: string | null
}
interface SearchArticlesResult {
  items: ArticleSummary[]
  pagination: { page: number; pageSize: number; totalItems: number; totalPages: number }
  appliedFilters: SearchFilter[]
  appliedSort: SearchSort[]
}
```

- **Observed response source:** `ArticlesService.summary`; todos los campos anteriores son realmente devueltos. API `codigo`, `nombre`, `corte`, `especie`, `mercado`, `pais_destino`, `temperatura`, `presentacion`, `envase_primario`, `envase_exterior`, `tipo_peso`, `peso_promedio_kg`, `activo`, `ficha_id` se normalizan a los nombres indicados.
- **Errors:** `INVALID_FILTER_FIELD`, `INVALID_FILTER_OPERATOR`, `INVALID_FILTER_VALUE`, `INVALID_PAGINATION`, `VALIDATION_ERROR`, más transporte.
- **State read:** `currentSearch` solo cuando el agent layer construye un refinamiento; la tool recibe el request final completo.
- **State write after success:** `currentSearch`, `lastSearch`; nueva búsqueda autosuficiente limpia `selectedArticleCodes`, refinamiento conserva selección solo si sus códigos siguen explícitamente seleccionados por el usuario. Regla V1 conservadora: limpiar selección al cambiar resultados.
- **Security:** no acepta SQL ni filtros no estructurados.

## 3. get_article

- **HTTP:** `GET /api/v1/articles/{codigo}`.
- **Visible input:** `{ articleCode: string }`.
- **HTTP mapping:** `articleCode` va como path segment escapado; nunca se acepta URL completa.
- **Validation:** string no vacío; formato exacto de código queda autoritativamente en API/dataset.
- **Normalized output:** preserva la estructura semántica completa observada, renombrando solo grupos a camelCase:

```ts
type ArticleGroup = Record<string, string | number | boolean | null>
interface ArticleDetail {
  identification: ArticleGroup
  productDestination: ArticleGroup
  codesAndAssociations: ArticleGroup
  packagingAndWeight: ArticleGroup
  labeling: ArticleGroup
  operationDates: ArticleGroup
  commercialOperations: ArticleGroup
  qualityAndSafety: ArticleGroup
  metadata: ArticleGroup
  technicalSheetId?: string
}
```

- **Observed mapping:** nueve grupos de `ArticleDocument`; no se inventan schemas exhaustivos para sus ~90 propiedades en esta etapa.
- **Errors:** `ARTICLE_NOT_FOUND`, transporte y desconocido.
- **State read:** ninguno dentro de la tool; el agent layer resuelve pronombres/ordinales antes.
- **State write:** `lastArticleCode`; agrega `RecentEntity(ARTICLE)`.
- **Security:** referencia debe estar resuelta; no acepta paths.

## 4. compare_articles

- **HTTP:** `POST /api/v1/articles/compare` (HTTP 201 actual).
- **Visible input:** `{ articleCodes: string[] }`.
- **HTTP mapping:** `articleCodes` → `codes`.
- **Validation:** entre 2 y 10 strings no vacíos y únicos.
- **Normalized output:**

```ts
interface ComparisonField {
  field: string
  values: Record<string, unknown>
  different: boolean
}
interface CompareArticlesResult {
  comparedArticleCodes: string[]
  fields: ComparisonField[]
  differentFieldsCount: number
  equalFieldsCount: number
}
```

- **Observed behavior:** conserva `null` en `values`; compara 21 fields publicados como comparables.
- **Errors:** `INVALID_COMPARISON`, `ARTICLE_NOT_FOUND`, validación y transporte.
- **State read:** códigos ya resueltos por agent layer desde selección/resultados.
- **State write:** `lastComparison.codes` y `selectedArticleCodes`; no cambia `currentSearch`.
- **Security:** no calcula diferencias localmente.

## 5. find_similar_articles

- **HTTP:** `POST /api/v1/articles/similar` (HTTP 201 actual).
- **Visible input:**

```ts
interface FindSimilarArticlesInput {
  referenceCode?: string
  features?: Record<string, unknown>
  required?: Record<string, unknown>
  limit?: number // integer 1..10
}
```

- **Validation:** exactamente uno de `referenceCode` o `features`; features no vacío; limit 1–10. API valida que features sean ponderables y required admisible.
- **HTTP mapping:** `referenceCode` → `reference_code`; otros objetos conservan field paths.
- **Normalized output:**

```ts
type EvaluationStatus = 'MATCH' | 'MISMATCH' | 'NOT_AVAILABLE'
type Eligibility = 'ELIGIBLE' | 'INELIGIBLE'
interface WeightedEvaluation {
  field: string; weight: number; referenceValue: unknown
  candidateValue: unknown; status: EvaluationStatus
}
interface RequiredEvaluation {
  field: string; requiredValue: unknown
  candidateValue: unknown; status: EvaluationStatus
}
interface SimilarCandidate {
  articleCode: string
  similarityScore: number
  eligibility: Eligibility
  weightedEvaluation: WeightedEvaluation[]
  requiredEvaluation: RequiredEvaluation[]
}
interface FindSimilarArticlesResult {
  criteriaUsed: { weighted: Record<string, unknown>; required: Record<string, unknown> }
  eligibleCandidates: SimilarCandidate[]
  ineligibleCandidates: SimilarCandidate[]
}
```

- **Invariant:** tool no interpreta obligatoriedad, recalcula score/eligibility ni reduce statuses a boolean.
- **Errors:** `INVALID_SIMILARITY_REQUEST`, `INVALID_REQUIRED_CRITERION`, `ARTICLE_NOT_FOUND`, validación y transporte.
- **State read:** referencia ya resuelta; la tool no lee lenguaje natural.
- **State write:** `lastSimilarity` guarda referencia/features, required y códigos por eligibility; no persiste scores como verdad permanente.
- **Security:** solo fields validados por API; nunca acepta funciones o expresiones.

## 6. get_technical_sheet

- **HTTP:** por `articleCode`, `GET /api/v1/articles/{codigo}/technical-sheet`; por `technicalSheetId`, `GET /api/v1/technical-sheets/{fichaId}`.
- **Visible input:**

```ts
interface GetTechnicalSheetInput {
  articleCode?: string
  technicalSheetId?: string
}
```

- **Validation:** exactamente un identificador no vacío. Se evita una union compleja para compatibilidad futura de tool schema; el adaptador aplica exactly-one.
- **Normalized output:**

```ts
interface TechnicalSheetResult {
  technicalSheetId: string
  articleCode: string
  title: string
  version: string
  language: string
  status: string
  createdAt: string
  updatedAt: string
  sourceNote: string
}
```

- **Observed limitation:** metadata solamente; no hay `sections` ni PDF.
- **Errors:** `TECHNICAL_SHEET_NOT_FOUND` por ID; por artículo inexistente el servicio devuelve actualmente `ARTICLE_NOT_FOUND`; transporte.
- **State read:** identificador resuelto fuera de la tool.
- **State write:** `lastTechnicalSheet` y `RecentEntity(TECHNICAL_SHEET)`.

## SavedFilter normalizado

```ts
interface SavedFilter {
  id: string
  ownerUserId: string // output informativo de API, nunca input del modelo
  name: string
  description: string | null
  search: SearchSpec
  createdAt: string
  updatedAt: string
}
```

El `search` persistido puede omitir defaults si así fue creado por la API. El adaptador los normaliza a `SearchSpec` al incorporarlo a `currentSearch`.

## 7. save_filter

- **HTTP:** `POST /api/v1/saved-filters` (HTTP 201).
- **Visible input:** `{ name: string; description?: string; search: SearchSpec }`.
- **Injected:** `X-Demo-User-Id` desde `AgentRequestContext.userId`.
- **Validation:** name 1–100, description máximo 500, search estructurado; API revalida ejecutando la búsqueda antes de guardar.
- **HTTP mapping:** search `pageSize` → `page_size`.
- **Output:** `SavedFilter`.
- **Errors:** errores de search, `DEMO_USER_REQUIRED`, `DEMO_USER_NOT_FOUND`, validación y transporte.
- **State read:** `currentSearch` es la fuente para “esta búsqueda”; si criterios vienen en el mismo turno, el agent layer puede llamar search primero para validarlos.
- **State write:** `lastSavedFilter`, entidad reciente.
- **Security:** userId no está en schema visible.

## 8. list_saved_filters

- **HTTP:** `GET /api/v1/saved-filters`.
- **Visible input:** `{}`.
- **Injected:** header de identidad.
- **Output:** `{ filters: SavedFilter[] }` normalizado (la API devuelve un array crudo).
- **Errors:** identidad, transporte y desconocido.
- **State read:** ninguno.
- **State write:** agrega filtros a `recentEntities` de forma acotada; no cambia `lastSavedFilter` salvo selección posterior.
- **Security:** ownership se aplica en API.

## 9. get_saved_filter

- **HTTP:** `GET /api/v1/saved-filters/{id}`.
- **Visible input:** `{ savedFilterId: string }`.
- **Injected:** identidad.
- **Output:** `SavedFilter`.
- **Errors:** `SAVED_FILTER_NOT_FOUND`, identidad y transporte.
- **State read:** ID resuelto desde state/list; no se inventa.
- **State write:** `lastSavedFilter` y entidad reciente.

## 10. execute_saved_filter

- **HTTP:** `POST /api/v1/saved-filters/{id}/execute` (HTTP 200).
- **Visible input:** `{ savedFilterId: string }`.
- **Injected:** identidad.
- **Output:** `SearchArticlesResult` (la API ejecuta el search almacenado y devuelve su resultado, no el filtro).
- **Errors:** `SAVED_FILTER_NOT_FOUND`, errores de search almacenado, identidad y transporte.
- **State read:** ID resuelto; para conocer nombre/search puede usarse `lastSavedFilter` o `get_saved_filter` si hace falta.
- **State write:** `currentSearch` con criterios del filtro, `lastSearch` con resultados actuales y `lastSavedFilter` cuando su metadata esté disponible; limpia selección.
- **Security:** siempre consulta datos actuales y ownership.

## 11. delete_saved_filter

- **HTTP:** `DELETE /api/v1/saved-filters/{id}` (HTTP 204 sin body).
- **Visible input:** `{ savedFilterId: string }`.
- **Injected:** identidad.
- **Output:** `{ deleted: true; savedFilterId: string }`, construido por el adaptador solo tras 204.
- **Errors:** `SAVED_FILTER_NOT_FOUND`, identidad y transporte.
- **State read:** ID resuelto; intent debe ser explícito e inequívoco.
- **State write:** elimina entidad correspondiente y limpia `lastSavedFilter` si coincide; no altera `currentSearch`.
- **Security:** no acepta userId; API aplica ownership.

## AgentRequestContext y CatalogApiClient

```ts
interface AgentRequestContext {
  userId: string
  conversationId: string
}
```

`CatalogApiClient` recibe base URL y timeout desde configuración, serializa requests, inyecta `X-Demo-User-Id` solo en operaciones personales, escapa path segments, normaliza responses y errores, y nunca expone credenciales o URLs internas al modelo. El timeout queda configurable; esta etapa no fija una duración arbitraria.

Arquitectura futura sugerida:

```text
apps/agent/
  agent/
  tools/
  clients/catalog-api.client
  state/
```

No se crean esos componentes ejecutables en esta etapa.

## Technical Decisions

1. Las tools exponen operaciones de dominio, no endpoints.
2. Los contratos internos usan camelCase; el cliente HTTP adapta snake_case.
3. La identidad y conversationId se inyectan fuera del LLM.
4. Todas las tools devuelven un envelope `ToolResult<T>` normalizado.
5. `get_technical_sheet` es una sola tool con exactly-one validado en el adaptador.
6. El estado guarda referencias y códigos, no objetos completos ni scores autoritativos.
7. Nombres de filtros se resuelven mediante list → nombre exacto/único → ID.
8. Delete inequívoco de filtro no requiere confirmación adicional en V1; referencia ambigua sí requiere aclaración.
9. Tool Result y UI Event son contratos distintos.
10. La deuda de response DTOs de OpenAPI no se compensa inventando schemas; estos contratos se derivan de services y tests.

## Diferencias y gaps observados

- OpenAPI declara status y request schemas, pero no response schemas detallados. Los outputs de este documento provienen de controller, service y e2e tests.
- El OpenAPI generado muestra dos entradas equivalentes para el header de identidad en `GET /saved-filters` (`X-Demo-User-Id` y `x-demo-user-id`). El cliente enviará una sola cabecera canónica `X-Demo-User-Id`.
- `CompareArticlesDto` anuncia 2–10 items en Swagger, pero sus decorators solo validan array/string; el service aplica realmente longitud y unicidad. La tool valida ambos antes de llamar y la API sigue siendo autoritativa.
- Los grupos completos de artículo son JSON flexibles (`Record<string, scalar>`), no DTOs de respuesta formalizados. Se preserva su estructura sin inventar un schema exhaustivo.
- `GET articles/{codigo}/technical-sheet` usa `ARTICLE_NOT_FOUND` también cuando no encuentra la relación de ficha. El dataset V1 es 1:1; una futura API podría distinguir artículo inexistente de ficha ausente.
- La API no ofrece lookup de filtro por nombre. La resolución requiere list → coincidencia única → ID.

No hay gaps que impidan los 20 flujos de Etapa 2. La formalización de response DTOs sigue siendo la recomendación principal antes de generar clientes automáticos.
