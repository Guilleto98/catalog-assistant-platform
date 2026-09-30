# Contrato conceptual de UI events

Este contrato prepara la futura separación entre lenguaje y representación estructurada:

```ts
interface AgentResponse {
  message: string
  ui?: AgentUiEvent
}
```

Angular no deberá parsear markdown para descubrir artículos, comparaciones o errores.

## Tipos V1 conceptuales

- `ARTICLE_SEARCH_RESULTS`
- `ARTICLE_DETAIL`
- `ARTICLE_COMPARISON`
- `SIMILARITY_RESULTS`
- `TECHNICAL_SHEET`
- `SAVED_FILTER_CREATED`
- `SAVED_FILTER_LIST`
- `CLARIFICATION`
- `ERROR`

El discriminated union conceptual vive en `packages/contracts/src/conceptual/ui-events.ts`.

## Separación de responsabilidades

`ToolResult` contiene datos normalizados suficientes para que el agente razone y explique. `AgentUiEvent` contiene una proyección seleccionada para representar visualmente. No son el mismo contrato y una tool no emite eventos de Angular directamente.

Ejemplo futuro:

```json
{
  "message": "Encontré 3 artículos que cumplen los criterios.",
  "ui": {
    "type": "ARTICLE_SEARCH_RESULTS",
    "data": {
      "filters": [],
      "articles": [],
      "totalItems": 3
    }
  }
}
```

Los payloads actuales son deliberadamente mínimos y podrán evolucionar cuando se defina el contrato Agent → Angular definitivo. No se implementa Angular ni serialización de responses en esta etapa.
