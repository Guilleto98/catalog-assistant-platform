# Agente

La Etapa 5A agrega ingreso de [adjuntos](attachments.md), el contrato
[ArticleRequestDraft](article-request-draft.md) y el
[flujo de análisis documental](document-intake-flow.md). El resultado es siempre
un borrador trazable con revisión humana, nunca un alta de catálogo.

La Etapa 2 define funcionalmente un solo agente raíz para el catálogo, con grounding estricto y contexto que no actúa como fuente de verdad. En esa etapa todavía no había ADK, prompts ejecutables, tools, storage ni Agent API.

- [Definición del agente](agent-definition.md)
- [Flujos conversacionales](conversational-flows.md)
- [Política de ambigüedad](ambiguity-policy.md)
- [Estado conversacional](conversation-state.md)
- [Matriz intent → capability](tool-intent-matrix.md)
- [Catálogo de tools V1](tool-catalog.md)
- [Contratos de tools](tool-contracts.md)
- [Política de errores](tool-error-policy.md)
- [Contrato de Agent State](agent-state-contract.md)
- [Reglas de ejecución](tool-execution-rules.md)
- [UI events conceptuales](ui-event-contract.md)
