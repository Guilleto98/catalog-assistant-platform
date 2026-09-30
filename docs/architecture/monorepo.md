# Organización del monorepo

La carpeta actual es la raíz única. npm actúa como punto de entrada a las tres aplicaciones; cada aplicación conserva su manifiesto y sus herramientas. No se usan workspaces, Nx ni Turborepo.

`apps/catalog-api` contiene la API NestJS, tests, Prisma, migraciones, seeds, Docker, OpenAPI, Postman y documentación específica.
`apps/agent` contiene el agente ADK, las tools, la Application API autenticada, persistencia, intake y tests Python.
`apps/web` contiene la aplicación Angular, clientes tipados generados, componentes, pruebas unitarias y pruebas de navegador.

`packages/contracts` conserva tipos conceptuales de las etapas iniciales; no es dependencia runtime ni fuente del cliente Angular. Los contratos HTTP vigentes se mantienen en `docs/contracts` y el tipo TypeScript se genera desde OpenAPI.

Los límites entre aplicaciones son deliberados: Angular habla con Application API; el agente consume Catalog API; Catalog API es fuente de verdad para el catálogo. Los scripts de raíz en `package.json` facilitan instalación, ejecución y pruebas sin convertir el repositorio en un workspace npm.

El [índice de documentación](../README.md) explica la ubicación de guías actuales, documentos del relevamiento histórico, fuentes, datos extraídos y salidas generadas.
