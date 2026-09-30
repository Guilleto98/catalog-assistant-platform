# Estado conversacional conceptual

Este documento define información necesaria para continuidad; no define storage ni persistencia.

| Campo | Contenido | Uso | Autoridad |
| --- | --- | --- | --- |
| `conversation_id` | Identificador de conversación | Correlación | Aplicación |
| `current_search` | Request estructurado vigente | Refinar y guardar | Referencia conversacional, no resultados actuales |
| `last_search_results` | Códigos ordenados y metadata mínima de la última respuesta | Ordinales y selección | Snapshot no autoritativo |
| `selected_article_codes` | Códigos seleccionados, en orden | Comparar, ver ficha, buscar similares | Referencias |
| `last_article_code` | Último artículo singular | Resolver “este/su” | Referencia |
| `last_comparison_codes` | Códigos de la última comparación | Resolver “los anteriores” | Referencia |
| `last_similarity_reference` | Código o features usados como referencia | Refinar similarity | Referencia |
| `last_similarity_request` | Request de similarity, incluido required | Repetir/refinar | Referencia estructurada |
| `last_similarity_results` | Códigos ordenados por grupo apto/no apto | Referencias ordinales | Snapshot no autoritativo |
| `last_technical_sheet` | IDs de ficha y artículo | Continuidad | Referencia; contenido reconsultable |
| `last_saved_filter` | ID y nombre del filtro relevante | Ejecutar, consultar o borrar | Referencia |
| `recent_entities` | Entidades mencionadas/mostradas, tipo, origen, turno y orden | Resolver pronombres | Referencia con alcance limitado |

## Forma conceptual de `current_search`

```json
{
  "filters": [
    {
      "field": "producto_destino.corte",
      "operator": "eq",
      "value": "BIFE_ANCHO"
    }
  ],
  "sort": [],
  "page": 1,
  "page_size": 20
}
```

## Transiciones de criterios

- `ADD`: incorpora un criterio no presente.
- `REPLACE`: sustituye el criterio del mismo campo cuando el usuario corrige o cambia el valor.
- `REMOVE`: elimina el criterio indicado.
- `KEEP`: conserva criterios no afectados.

El refinamiento normalmente agrega y reinicia la página a 1. Una corrección explícita reemplaza; “me da igual” elimina. No se convierten dos valores sucesivos del mismo campo en `in` salvo que el usuario pida ambos.

## Actualización por operación

- Search exitoso: escribe `current_search`, `last_search_results` y `recent_entities`.
- Refinamiento: lee `current_search`, aplica ADD/REPLACE/REMOVE/KEEP y actualiza resultados.
- Detail: escribe `last_article_code` y la entidad reciente.
- Compare: lee códigos explícitos/seleccionados y escribe `last_comparison_codes`.
- Similar: escribe referencia, request, resultados y entidades recientes, separadas por eligibility.
- Technical sheet: escribe solo identificadores y metadata necesaria de `last_technical_sheet`.
- Save: lee exactamente `current_search` y escribe referencia del filtro creado.
- List/get: actualiza referencias a filtros sin sustituir `current_search`.
- Execute saved filter: consulta la API, escribe la búsqueda ejecutada como `current_search` y nuevos resultados.
- Delete: elimina del estado la referencia borrada si coincide con `last_saved_filter`.

Una aclaración pendiente no debe mutar el estado operativo como si la acción hubiera ocurrido.

## Información no autoritativa

No se usan como verdad permanente datos completos de artículo, scores, eligibility, ficha o resultados guardados. Se recuerdan códigos e identificadores para reconsultar. Ejecutar un filtro guardado siempre obtiene datos actuales; no reproduce resultados viejos de la conversación.

## Alcance y conflicto

Las referencias deben registrar origen y turno para detectar ambigüedad entre varios conjuntos recientes. Si el estado no permite identificar un antecedente de forma inequívoca, se aclara. El usuario puede corregir cualquier interpretación; la corrección reemplaza el valor anterior y dispara una nueva lectura cuando corresponda.
