# Contratos compartidos conceptuales

Este paquete conserva los modelos conceptuales TypeScript creados en la Etapa 3 para Agent State, resultados de tools y eventos de UI. Son material de diseño y referencia: no constituyen una librería publicada, no se importan en runtime y no describen el contrato HTTP vigente de Application API.

Para Application API, la fuente canónica actual es [`docs/contracts/application-api-v1.openapi.json`](../../../docs/contracts/application-api-v1.openapi.json), acompañada por su [guía legible](../../../docs/contracts/application-api-v1.md). Los tipos del frontend se generan en `apps/web/src/app/api/generated/application-api.ts` mediante `npm run web:contracts`. Los conceptos de Agent State siguen documentados en [`docs/agent/agent-state-contract.md`](../../../docs/agent/agent-state-contract.md).

Principios:

- nombres internos en `camelCase`;
- `CatalogApiClient` adapta a los nombres HTTP `snake_case`;
- identidad y conversación se inyectan desde contexto seguro;
- el estado guarda referencias, no el catálogo completo;
- `ToolResult` y `AgentUiEvent` son capas diferentes.

Archivos:

- `src/conceptual/agent-state.ts`: contexto seguro, estado y transiciones conceptuales;
- `src/conceptual/tool-result.ts`: envelope normalizado y error seguro;
- `src/conceptual/ui-events.ts`: eventos estructurados futuros para Angular.

No contiene implementación HTTP, ADK, persistencia ni UI. No cambiar aquí los DTOs de Application API; se actualizan en su OpenAPI y luego se regeneran los tipos de Angular.
