# Índice de documentación

Este índice reúne la documentación vigente del producto y sus aplicaciones.

## Producto actual

- [`architecture/`](architecture/): arquitectura del sistema y organización del monorepo.
- [`agent/`](agent/): agente, herramientas, políticas conversacionales, dominio y estado.
- [`platform/`](platform/): identidad, conversaciones, persistencia y auditoría.
- [`contracts/`](contracts/): contrato HTTP Application API vigente, OpenAPI y ejemplos.
- [`web/`](web/): arquitectura, experiencia de usuario y entregas de Angular.
- [`evals/`](evals/): escenarios de evaluación y pruebas de comportamiento.
- La documentación operativa de Catalog API está en [`apps/catalog-api/docs`](../apps/catalog-api/docs/).

Los archivos de relevamiento, especificaciones de terceros, notas de reuniones y propuestas específicas de cliente se conservan en la copia de trabajo y están excluidos de publicación.

## Fuentes canónicas por tema

- API de catálogo: [`apps/catalog-api/docs/openapi.json`](../apps/catalog-api/docs/openapi.json) y documentación de esa aplicación.
- API autenticada del agente: [`contracts/application-api-v1.openapi.json`](contracts/application-api-v1.openapi.json).
- Tipos de Angular: generados desde ese OpenAPI en `apps/web/src/app/api/generated/`; ejecutar `npm run web:contracts` para regenerarlos.
- Estado conceptual del agente: [`agent/agent-state-contract.md`](agent/agent-state-contract.md); no reemplaza los DTOs HTTP.
