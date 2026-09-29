# Uruguay Meat Catalog API

API local y educativa para explorar un catálogo de 50 artículos sintéticos de la industria cárnica uruguaya. Ofrece búsqueda tipada, comparación, similitud determinística, requisitos obligatorios, fichas ficticias y filtros personales de usuarios demo.

> **Todos los datos son 100 % sintéticos y educativos.** No representan artículos, códigos, parámetros, certificaciones, fichas, límites sanitarios ni APIs reales de ninguna empresa u organismo. Las vidas útiles no son recomendaciones oficiales.

## Qué no es

No incluye Google ADK, agentes, chat, LLM, embeddings, RAG, autenticación real ni integraciones externas. `X-Demo-User-Id` solo simula ownership local y **no es autenticación segura**.

## Stack y organización

- Node.js 22 LTS ejecuta la aplicación; TypeScript aporta contratos explícitos.
- NestJS organiza entrada HTTP en controllers, validación en DTOs y lógica en services.
- Prisma accede a SQLite; el catálogo se guarda en grupos JSON y columnas índice simples.
- Swagger publica el contrato OpenAPI en `http://localhost:3000/api/docs`.
- Jest y Supertest verifican reglas y endpoints; ESLint y Prettier mantienen el código.
- Docker Compose permite ejecutar todo sin instalar Node localmente.

El recorrido normal es `HTTP → Controller → DTO validation → Service → Prisma → SQLite → Response`. Véase [docs/architecture.md](docs/architecture.md).

## Instalación y ejecución sin Docker

Requiere Node.js 22 LTS y npm.

```bash
npm install
npm run db:generate
npm run db:reset
npm run start:dev
```

La API queda en `http://localhost:3000/api/v1` y Swagger en `http://localhost:3000/api/docs`.

Para reiniciar exactamente el dataset V1: `npm run db:reset`. Este comando aplica las migraciones pendientes y el seed elimina el contenido de las cuatro tablas antes de volver a cargar los JSON versionados. Está diseñado exclusivamente para la SQLite local de esta demo; nunca debe apuntarse a una base productiva.

## Ejecución con Docker

```bash
docker compose up --build
```

El volumen `catalog_sqlite` persiste SQLite. El contenedor aplica migraciones y recarga el seed al iniciar.

## Calidad y pruebas

```bash
npm run build
npm run lint
npm run test
npm run test:e2e
```

## Dataset

Los archivos fuente están en `data/seed/`: `articles.v1.json`, `technical-sheets.v1.json` y `demo-users.v1.json`. Son 50 artículos (`900001`–`900050`), 50 fichas 1:1, 42 activos y 8 inactivos. Cada artículo contiene nueve grupos de dominio y 90 propiedades. El seed y sus timestamps son determinísticos.

Usuarios: `demo-user-01` (Usuario Demo 1) y `demo-user-02` (Usuario Demo 2). Todos los endpoints `/saved-filters` requieren el header `X-Demo-User-Id`.

## Endpoints

| Método          | Ruta                                       | Propósito                         |
| --------------- | ------------------------------------------ | --------------------------------- |
| GET             | `/api/v1/health`                           | Estado y conteo                   |
| GET             | `/api/v1/metadata/filterable-fields`       | Contrato de filtros               |
| POST            | `/api/v1/articles/search`                  | Búsqueda, sort y paginación       |
| GET             | `/api/v1/articles/:codigo`                 | Artículo completo                 |
| POST            | `/api/v1/articles/compare`                 | Comparación de 2–10 artículos     |
| POST            | `/api/v1/articles/similar`                 | Similitud y aptitud               |
| GET             | `/api/v1/technical-sheets/:fichaId`        | Ficha por ID                      |
| GET             | `/api/v1/articles/:codigo/technical-sheet` | Ficha por artículo                |
| POST/GET/DELETE | `/api/v1/saved-filters...`                 | CRUD acotado y ejecución personal |

## Ejemplos curl

```bash
curl localhost:3000/api/v1/health
curl localhost:3000/api/v1/metadata/filterable-fields
curl -X POST localhost:3000/api/v1/articles/search -H 'Content-Type: application/json' -d '{"filters":[{"field":"producto_destino.corte","operator":"eq","value":"BIFE_ANCHO"}]}'
curl localhost:3000/api/v1/articles/900001
curl -X POST localhost:3000/api/v1/articles/compare -H 'Content-Type: application/json' -d '{"codes":["900001","900002","900003"]}'
curl -X POST localhost:3000/api/v1/articles/similar -H 'Content-Type: application/json' -d '{"reference_code":"900001","limit":5}'
curl -X POST localhost:3000/api/v1/articles/similar -H 'Content-Type: application/json' -d '{"reference_code":"900001","required":{"producto_destino.mercado":"CHINA","producto_destino.temperatura":"CONGELADO"},"limit":5}'
curl localhost:3000/api/v1/articles/900001/technical-sheet
curl -X POST localhost:3000/api/v1/saved-filters -H 'Content-Type: application/json' -H 'X-Demo-User-Id: demo-user-01' -d '{"name":"China congelados","search":{"filters":[{"field":"producto_destino.mercado","operator":"eq","value":"CHINA"},{"field":"producto_destino.temperatura","operator":"eq","value":"CONGELADO"}],"sort":[]}}'
curl localhost:3000/api/v1/saved-filters -H 'X-Demo-User-Id: demo-user-01'
curl -X POST localhost:3000/api/v1/saved-filters/REEMPLAZAR_ID/execute -H 'X-Demo-User-Id: demo-user-01'
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Diccionario de campos](docs/field_dictionary.md)
- [Consultas de referencia](docs/reference_queries.md)
- [Mutaciones futuras](docs/future_mutations.md)
- [Capacidades futuras](docs/future_capabilities.md)
- [Colección Postman lista para importar](docs/postman/Uruguay-Meat-Catalog-API.postman_collection.json)

## Limitaciones V1

El catálogo pequeño se filtra determinísticamente en memoria después de leer los 50 registros; SQLite conserva la persistencia y columnas índice preparan una evolución. Las fichas solo tienen metadatos, los filtros guardados sí mutan datos locales y no existe autorización real. Agrupaciones, rankings y edición de artículos están deliberadamente fuera de alcance.
