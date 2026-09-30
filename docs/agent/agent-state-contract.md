# Contrato de Agent State V1

El estado permite continuidad conversacional; no es base de datos ni fuente de verdad del catálogo. Los datos actuales se reconsultan.

## Estado runtime implementado hasta Etapa 5A.2

| Grupo | Keys | Uso |
|---|---|---|
| Catálogo | `current_search`, `last_search_codes`, `last_article_code`, `last_comparison_codes` | Continuidad, refinamientos y referencias ordinales |
| Intake | `conversation_id`, `current_attachment_ids`, `current_request_draft_id` | Referencias a recursos persistidos, nunca binarios |
| Domain scope | `domain_scope_decision`, `domain_scope_reason`, `domain_scope_latency_ms`, `domain_scope_root_skipped` | Debug, trace y auditoría del turno actual |

Las keys de scope no son fuente de verdad funcional y se recalculan en cada
invocación. Session State no guarda PDF, XLSX, audio, transcripciones completas,
contenido documental parseado ni resultados completos del catálogo.

El resto de este documento conserva el contrato conceptual ampliado para etapas
futuras; no implica que todas esas capacidades ya estén expuestas por el Agent.

## Separación de contexto seguro

```ts
interface AgentRequestContext {
  userId: string
  conversationId: string
}
```

`AgentRequestContext` es creado por Agent Backend desde la request autenticada/demo. No es tool input ni contenido editable por el LLM. `userId` se convierte en `X-Demo-User-Id` solo dentro de `CatalogApiClient`; `conversationId` correlaciona state y trazas futuras.

## AgentState

```ts
interface AgentState {
  conversationId: string
  currentSearch: CurrentSearch | null
  lastSearch: {
    articleCodes: string[]
    page: number
    totalItems: number
  } | null
  selectedArticleCodes: string[]
  lastArticleCode: string | null
  lastComparison: { codes: string[] } | null
  lastSimilarity: {
    referenceCode?: string
    features?: Record<string, unknown>
    required?: Record<string, unknown>
    eligibleCodes: string[]
    ineligibleCodes: string[]
  } | null
  lastTechnicalSheet: {
    technicalSheetId: string
    articleCode?: string
  } | null
  lastSavedFilter: { id: string; name: string } | null
  recentEntities: RecentEntity[]
}
```

El tipo conceptual compartido vive en `packages/contracts/src/conceptual/agent-state.ts`.

## CurrentSearch

```ts
interface CurrentSearch {
  filters: SearchFilter[]
  sort: SearchSort[]
  page: number
  pageSize: number
}
```

Es el request completo normalizado y permite:

- ADD: incorporar criterio nuevo;
- REPLACE: sustituir criterio del mismo field;
- REMOVE: quitar criterio;
- KEEP: conservar criterios no afectados.

Toda modificación de filtros vuelve a page 1. Dos valores sucesivos no se convierten en `in` salvo pedido explícito.

## RecentEntity

```ts
interface RecentEntity {
  type: 'ARTICLE' | 'SAVED_FILTER' | 'TECHNICAL_SHEET'
  id: string
  label?: string
}
```

La lista es pequeña, ordenada por recencia y sirve para resolver “ese” o “el anterior”. El límite concreto se decidirá al implementar; no se convierte en historial completo.

## Estado inicial y aislamiento

Una conversación nueva crea:

```text
currentSearch = null
lastSearch = null
selectedArticleCodes = []
lastArticleCode = null
lastComparison = null
lastSimilarity = null
lastTechnicalSheet = null
lastSavedFilter = null
recentEntities = []
```

No hereda selecciones ni resultados de otra conversación. El `conversationId` del state debe coincidir con el contexto seguro antes de leer o escribir.

## Transiciones exactas por tool

| Tool | State read | State write on success | Preserved/cleared |
| --- | --- | --- | --- |
| `get_filterable_fields` | Ninguno | Ninguno | Todo preservado |
| `search_articles` | `currentSearch` solo si agent layer prepara refinamiento | `currentSearch`; `lastSearch` con codes/page/total; articles en `recentEntities` | Limpia `selectedArticleCodes`; preserva otros last-* como historial referencial |
| `get_article` | Código ya resuelto desde resultados/entities | `lastArticleCode`; ARTICLE reciente | No cambia search/selection |
| `compare_articles` | Códigos ya resueltos/seleccionados | `lastComparison.codes`; `selectedArticleCodes=codes`; ARTICLE recientes | No cambia `currentSearch` |
| `find_similar_articles` | Referencia ya resuelta | referencia/features, required, eligible/ineligible codes; ARTICLE recientes | No guarda scores; no cambia search |
| `get_technical_sheet` | Artículo/ficha ya resuelto | `lastTechnicalSheet`; TECHNICAL_SHEET reciente | No cambia search |
| `save_filter` | `currentSearch` para “esta búsqueda” | `lastSavedFilter`; SAVED_FILTER reciente | No cambia search |
| `list_saved_filters` | Ninguno | SAVED_FILTER entities acotadas | No cambia `lastSavedFilter` automáticamente |
| `get_saved_filter` | ID resuelto | `lastSavedFilter`; entity | No cambia search |
| `execute_saved_filter` | ID; metadata de filtro si disponible | `currentSearch`; `lastSearch`; `lastSavedFilter`; results/entities | Limpia selección; datos son actuales |
| `delete_saved_filter` | ID resuelto | Elimina entity; limpia `lastSavedFilter` si coincide | No borra `currentSearch` aunque provenga de ese filtro |

Una tool fallida no aplica su transición de éxito. Puede registrarse error efímero para la respuesta, pero no se agrega a este state V1.

## Selección

`selectedArticleCodes` representa una selección explícita, no todos los resultados visibles. “Compará el primero y el tercero” resuelve posiciones desde `lastSearch.articleCodes`, llama compare y luego fija la selección a esos códigos. Una búsqueda o ejecución de filtro nueva limpia selección para evitar que “estos” apunte a una lista vieja.

## Datos deliberadamente ausentes

No se guardan artículos completos, comparaciones completas, fichas completas, results completos, similarity scores ni eligibility como verdad permanente. Se guardan identificadores y criterios necesarios para continuar. Una consulta que exige actualidad vuelve a usar tools.
