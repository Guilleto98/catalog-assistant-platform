# Arquitectura

## Recorrido de una request

`HTTP request → Controller → DTO validation → Service → Prisma / SQLite → Response`

El **controller** define la ruta y recibe parámetros. El `ValidationPipe` global transforma y valida el body con un **DTO**; además rechaza propiedades no declaradas. El **service** aplica reglas de negocio. `PrismaService` traduce operaciones tipadas a SQLite. Un filtro global convierte errores esperados al contrato `{ error: { code, message, details } }` y oculta stacks.

### Search

1. `ArticlesController` recibe `POST /articles/search`.
2. `SearchArticlesDto` valida estructura y límites básicos.
3. `ArticlesService` coteja field, operator y value con `FIELD_METADATA`.
4. Prisma carga los 50 artículos de SQLite.
5. El service filtra, ordena, pagina y proyecta un resumen.
6. La respuesta incluye totales reales y criterios aplicados.

### Compare

El DTO limita la lista a 2–10 códigos únicos. El service carga los artículos, recorre la metadata comparable y considera `null` un valor. `different` es exactamente `cantidad de valores distintos > 1`.

### Similar

`SimilarityService` acepta un artículo de referencia o features, nunca ambos. Evalúa los ocho campos ponderados con `MATCH`, `MISMATCH` o `NOT_AVAILABLE`; el ausente conserva su peso en el denominador. En paralelo evalúa `required`: solo todos `MATCH` producen `ELIGIBLE`. Luego separa conjuntos y ordena por score descendente y código ascendente.

### Saved filters

El controller lee `X-Demo-User-Id`; el service verifica el usuario y siempre consulta por `id + ownerUserId`. Guarda el request de búsqueda, no resultados. Ejecutar vuelve a llamar `ArticlesService.search`, por lo que usa datos actuales. Un recurso ajeno se presenta como inexistente.

## Carpetas

- `src/articles`: búsqueda, detalle y comparación.
- `src/similarity`: score y aptitud.
- `src/technical-sheets`: metadatos de fichas.
- `src/saved-filters`: ownership y persistencia personal.
- `src/metadata`: descubrimiento de campos filtrables.
- `src/common`: errores, tipos y contrato central de campos.
- `src/database`: cliente Prisma compartido.
- `prisma`: esquema, migración y seed.
- `data/seed`: fuente JSON reproducible.
- `test`: suites unitarias/e2e y benchmarks de referencia.

## Technical decisions

1. **Grupos JSON más columnas índice.** Mantiene la respuesta anidada legible y evita 90 columnas físicas. Código, activo, corte, mercado, país, temperatura y vida útil también existen como columnas para evolución. Para solo 50 filas, la búsqueda usa la única metadata central y filtrado en memoria: privilegia claridad y permite todos los operadores sin SQL dinámico.
2. **Metadata única.** `FIELD_METADATA` alimenta validación, endpoint metadata, comparación y documentación; evita whitelists divergentes.
3. **Seed JSON versionado.** Un generador determinístico existe para mantenimiento, pero Prisma siempre consume los JSON guardados. Los tests fijan hashes SHA-256.
4. **IDs de filtros UUID.** Solo los recursos creados durante uso son no determinísticos; el catálogo V1 sí es idéntico en cada reset.
5. **Fichas 1:1.** Es una simplificación educativa, no un modelo real.

## Supuestos ficticios

Todo el stack, rutas, códigos 900001–900050, campos, usuarios, packaging, mercados, pesos, vidas útiles, timestamps, scoring, aptitud y relación ficha/artículo son decisiones de esta demo. No describen sistemas ni políticas reales de ninguna empresa u organismo.
