# Consultas de referencia V1

Estos casos son benchmarks determinísticos y están asociados a `test/api.e2e-spec.ts`. Las listas conservan el orden por defecto (`identificacion.codigo ASC`).

## Caso A — corte + mercado

```http
POST /api/v1/articles/search
Content-Type: application/json

{"filters":[{"field":"producto_destino.corte","operator":"eq","value":"BIFE_ANCHO"},{"field":"producto_destino.mercado","operator":"eq","value":"CHINA"}],"page_size":50}
```

`expected_codes: ["900001"]`; `total_items: 1`.

## Caso B — vida útil

```json
{
  "filters": [{ "field": "producto_destino.vida_util", "operator": "gte", "value": 395 }],
  "page_size": 50
}
```

`expected_codes: ["900031","900034","900035","900036","900039","900040","900041","900044","900045","900046","900049","900050"]`; `total_items: 12`.

La vida útil está expresada en días y es un dato sintético, no una recomendación.

## Caso C — código INAC ausente

```json
{
  "filters": [{ "field": "codigos_asociaciones.codigo_inac", "operator": "is_null" }],
  "page_size": 50
}
```

`expected_codes: ["900007","900014","900021","900028","900035","900042","900049"]`; `total_items: 7`.

## Caso D — comparación conocida

```http
POST /api/v1/articles/compare
Content-Type: application/json

{"codes":["900001","900002","900003"]}
```

Resultado exacto: `different_fields_count: 15`, `equal_fields_count: 6`. Los paths diferentes son:

```text
identificacion.codigo
identificacion.nombre
producto_destino.presentacion
producto_destino.mercado
producto_destino.pais_destino
producto_destino.temperatura
producto_destino.vida_util
codigos_asociaciones.codigo_inac
codigos_asociaciones.codigo_cliente
envase_pesaje.envase_primario
envase_pesaje.envase_exterior
envase_pesaje.tipo_peso
envase_pesaje.peso_promedio_kg
etiquetado.idioma_etiqueta
etiquetado.rito
```

## Caso E — score alto pero requisito incumplido

```json
{
  "reference_code": "900001",
  "required": { "producto_destino.mercado": "CHINA", "producto_destino.temperatura": "CONGELADO" },
  "limit": 10
}
```

Resultados exactos `eligible_candidates` como pares `[codigo, score]`:

```json
[
  ["900006", 70],
  ["900016", 55],
  ["900021", 55],
  ["900026", 55],
  ["900031", 55],
  ["900036", 55],
  ["900041", 55],
  ["900046", 55],
  ["900011", 50]
]
```

Los primeros diez `ineligible_candidates` son:

```json
[
  ["900004", 90],
  ["900002", 80],
  ["900005", 80],
  ["900003", 60],
  ["900009", 60],
  ["900007", 50],
  ["900010", 50],
  ["900014", 45],
  ["900019", 45],
  ["900024", 45]
]
```

Así, `900004` tiene score 90 pero es `INELIGIBLE` porque su mercado es `UE`; `900006` sí es `ELIGIBLE` con score 70. Aptitud y similitud no se mezclan.

## Caso F — ningún candidato apto

```json
{
  "reference_code": "900001",
  "required": { "producto_destino.mercado": "CHINA", "producto_destino.presentacion": "CON_HUESO" },
  "limit": 10
}
```

Resultado exacto relevante: `eligible_candidates: []`. La API conserva candidatos descartados en `ineligible_candidates`; nunca asciende al mejor score a apto.
