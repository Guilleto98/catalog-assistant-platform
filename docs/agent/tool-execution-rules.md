# Reglas de ejecución de tools

## Reglas generales

1. Las lecturas inequívocas no requieren confirmación.
2. No inventar argumentos, fields, enums, IDs ni referencias.
3. No llamar una tool con pronombre u ordinal sin resolver.
4. No repetir una llamada exitosa sin necesidad de actualidad, paginación, corrección o reintento solicitado.
5. No presentar snapshots del state como resultados actuales.
6. Search no se reemplaza por similarity por tener muchos criterios.
7. Compare no se usa para descubrir similares; similarity no se usa para explicar diferencias entre una lista fija.
8. No llamar `get_article` para cada summary de search salvo pedido de detalle o necesidad de un dato no presente.
9. No usar memoria para responder un dato autoritativo que debe verificarse.
10. `userId`, `conversationId`, base URL y headers nunca provienen del modelo.

## Uso eficiente

“Buscame bife ancho para China” normalmente requiere una sola llamada a `search_articles`. `get_filterable_fields` solo se agrega cuando el mapping no es seguro. No se encadena detalle para cada resultado.

“¿Cuál es el peso del 900001?” requiere `get_article`, incluso si ese dato apareció antes: la API es la fuente actual.

## Chaining permitido

### Guardar criterios

- Existe `currentSearch`: `save_filter` directamente con ese objeto.
- No existe state, pero el mismo mensaje contiene criterios: interpretar → `search_articles` para validar/obtener resultados → `save_filter` solo si search fue exitoso y la intención de guardar es clara.
- No existen state ni criterios: aclarar; no guardar filtro vacío.

La búsqueda previa a save no es obligatoria si ya existe un `currentSearch` válido.

### Filtro por nombre

Para ejecutar, consultar o borrar “China congelados” sin ID conocido:

```text
list_saved_filters
→ comparar nombre de forma exacta/case-insensitive normalizada
→ si hay una coincidencia: usar su ID
→ si hay cero: informar no encontrado
→ si hay más de una: pedir aclaración
```

Nunca inventar ID. Si `lastSavedFilter` coincide inequívocamente con la referencia, puede omitirse list.

### Ficha

Resolver primero artículo o ficha. Una sola llamada a `get_technical_sheet`; no llamar ambos endpoints para comprobar igualdad.

## Similarity

- Enviar exactamente referenceCode o features.
- `required` solo contiene obligatoriedad ya interpretada por el agente.
- Preservar `MATCH`, `MISMATCH`, `NOT_AVAILABLE`, `ELIGIBLE` e `INELIGIBLE`.
- Mostrar aptos antes que no aptos cuando hay requisitos.
- No recalcular ni reordenar mezclando eligibility con score.

## Errores y reintentos

- Validation/not found: no reintentar sin cambiar argumentos o recibir nueva información.
- Upstream/timeout retryable: como máximo un reintento automático futuro si la política operativa lo autoriza; no se fija aquí. Evitar loops.
- Fallo: no escribir transición de éxito ni usar datos anteriores como respuesta actual.
- Si el error revela un field/enum inválido, puede consultarse metadata antes de pedir una aclaración.

## Escrituras V1

- `save_filter`: requiere nombre y search válido; guarda criterios, no resultados.
- `delete_saved_filter`: ejecutar directamente solo con intención y target inequívocos. Si “ese” puede referir a varios filtros, aclarar.
- Ninguna regla de bajo riesgo para filtros se extiende a futuras mutaciones de artículos.

## Trazabilidad futura

El backend podrá registrar conversationId, tool, argumentos saneados, duración y success/error. No se implementa ahora y no se envían trazas internas al modelo.

## Cobertura de Etapa 2

| Flows | Soporte |
| --- | --- |
| CF/EV-01–05, 13–14, 19 | `search_articles` + `CurrentSearch` + metadata/error policy |
| CF/EV-06–07 | `get_article` + lastSearch/lastArticle |
| CF/EV-08–09 | `compare_articles` + selection/comparison state |
| CF/EV-10–12 | `find_similar_articles` + similarity state/statuses |
| CF/EV-15 | `save_filter` + currentSearch + request context |
| CF/EV-16 | list/name resolution + execute + state transition |
| CF/EV-17 | `get_technical_sheet` + lastArticle |
| CF/EV-18 | ambiguity policy; ninguna tool hasta resolver |
| CF/EV-20 | `ToolError` y política de transporte |

Todos los 20 flujos tienen tool/input/state/error support. No se encontró un gap funcional bloqueante.

## Fixtures futuros de integración

- `BIFE_ANCHO + CHINA`;
- vida útil `gte 395`;
- `codigo_inac is_null`;
- comparación `900001/900002/900003`, incluyendo null en otros pares;
- similarity `900001` con required China+Congelado;
- similarity sin candidatos eligible;
- ownership inyectado fuera del modelo;
- error API → `ToolError`.
