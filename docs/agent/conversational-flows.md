# Flujos conversacionales V1

Estos flujos describen comportamiento generalizable, no reglas por coincidencia literal.

## CF-01 — Búsqueda simple

**ID**  
CF-01

**Goal**  
Buscar por un atributo suficiente.

**Starting context**  
Sin búsqueda previa necesaria.

**User message**  
“Buscame bife ancho.”

**Expected interpretation**  
`SEARCH_ARTICLES`; criterio de corte.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**
```json
{"filters":[{"field":"producto_destino.corte","operator":"eq","value":"BIFE_ANCHO"}]}
```

**State read**  
Metadata solo si hiciera falta validar el mapping.

**State update**  
Escribe `current_search`, resultados ordenados y entidades recientes.

**Expected response behavior**  
Mostrar criterio interpretado, cantidad y resultados; ofrecer refinamiento opcional.

**Forbidden behavior**  
Exigir mercado, temperatura, envase o peso antes de buscar.

## CF-02 — Búsqueda múltiple

**ID**  
CF-02

**Goal**  
Combinar criterios explícitos.

**Starting context**  
Ninguno.

**User message**  
“Buscame bife ancho congelado para China.”

**Expected interpretation**  
`SEARCH_ARTICLES` con corte, temperatura y mercado.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**
```json
{"filters":[{"field":"producto_destino.corte","operator":"eq","value":"BIFE_ANCHO"},{"field":"producto_destino.temperatura","operator":"eq","value":"CONGELADO"},{"field":"producto_destino.mercado","operator":"eq","value":"CHINA"}]}
```

**State read**  
Metadata.

**State update**  
Reemplaza `current_search` y resultados.

**Expected response behavior**  
Transparentar los tres criterios y el resultado.

**Forbidden behavior**  
Usar similarity por haber varios criterios.

## CF-03 — Refinamiento aditivo

**ID**  
CF-03

**Goal**  
Acotar la búsqueda vigente.

**Starting context**  
`current_search`: corte `BIFE_ANCHO`.

**User message**  
“Solo los de China.”

**Expected interpretation**  
ADD mercado `CHINA`; KEEP corte.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**
```json
{"filters":[{"field":"producto_destino.corte","operator":"eq","value":"BIFE_ANCHO"},{"field":"producto_destino.mercado","operator":"eq","value":"CHINA"}],"page":1}
```

**State read**  
`current_search`.

**State update**  
Actualiza búsqueda y resultados.

**Expected response behavior**  
Indicar que mantuvo corte y agregó mercado.

**Forbidden behavior**  
Descartar silenciosamente el corte anterior.

## CF-04 — Reemplazo de criterio

**ID**  
CF-04

**Goal**  
Corregir un filtro existente.

**Starting context**  
`current_search` contiene mercado `CHINA`.

**User message**  
“No, mejor Brasil.”

**Expected interpretation**  
REPLACE mercado por `BRASIL`; KEEP los demás criterios.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**  
La búsqueda previa con un único criterio de mercado `BRASIL` y página 1.

**State read**  
`current_search`.

**State update**  
Elimina `CHINA`, guarda `BRASIL` y nuevos resultados.

**Expected response behavior**  
Confirmar brevemente la corrección y mostrar resultados nuevos.

**Forbidden behavior**  
Convertirlo en `mercado in [CHINA, BRASIL]`.

## CF-05 — Eliminación de criterio

**ID**  
CF-05

**Goal**  
Quitar una restricción.

**Starting context**  
`current_search` contiene temperatura `CONGELADO` y otros criterios.

**User message**  
“La temperatura me da igual.”

**Expected interpretation**  
REMOVE temperatura; KEEP los restantes.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**  
Búsqueda anterior sin el filtro `producto_destino.temperatura`, página 1.

**State read**  
`current_search`.

**State update**  
Actualiza búsqueda y resultados.

**Expected response behavior**  
Mostrar que temperatura ya no se aplica.

**Forbidden behavior**  
Mantener el filtro o reemplazarlo por otro enum.

## CF-06 — Detalle por código

**ID**  
CF-06

**Goal**  
Consultar un artículo explícito.

**Starting context**  
Ninguno.

**User message**  
“Mostrame el 900001.”

**Expected interpretation**  
`GET_ARTICLE` para `900001`.

**Clarification required?**  
No.

**Expected capability**  
`get_article`

**Expected structured arguments**
```json
{"codigo":"900001"}
```

**State read**  
Ninguno.

**State update**  
`last_article_code = 900001`; entidad reciente.

**Expected response behavior**  
Resumir datos verificados de la API.

**Forbidden behavior**  
Completar campos ausentes con conocimiento del modelo.

## CF-07 — Referencia ordinal

**ID**  
CF-07

**Goal**  
Resolver una posición visible.

**Starting context**  
Últimos resultados ordenados: `900001`, `900004`, `900006`.

**User message**  
“Mostrame el segundo.”

**Expected interpretation**  
`GET_ARTICLE` para `900004`.

**Clarification required?**  
No.

**Expected capability**  
`get_article`

**Expected structured arguments**
```json
{"codigo":"900004"}
```

**State read**  
`last_search_results` y su orden visible.

**State update**  
`last_article_code = 900004`.

**Expected response behavior**  
Consultar la API y presentar el detalle actual.

**Forbidden behavior**  
Responder solo desde el snapshot de resultados.

## CF-08 — Comparación explícita

**ID**  
CF-08

**Goal**  
Comparar tres artículos conocidos.

**Starting context**  
Ninguno.

**User message**  
“Compará 900001, 900002 y 900003.”

**Expected interpretation**  
`COMPARE_ARTICLES`.

**Clarification required?**  
No.

**Expected capability**  
`compare_articles`

**Expected structured arguments**
```json
{"codes":["900001","900002","900003"]}
```

**State read**  
Ninguno.

**State update**  
Guarda los tres en `last_comparison_codes`.

**Expected response behavior**  
Priorizar diferencias devueltas y resumir coincidencias relevantes.

**Forbidden behavior**  
Calcular diferencias por memoria o convertirlo en similarity.

## CF-09 — Comparación contextual

**ID**  
CF-09

**Goal**  
Comparar la selección inequívoca.

**Starting context**  
`selected_article_codes = [900001, 900004]`.

**User message**  
“Comparalos.”

**Expected interpretation**  
`COMPARE_ARTICLES` sobre la selección.

**Clarification required?**  
No.

**Expected capability**  
`compare_articles`

**Expected structured arguments**
```json
{"codes":["900001","900004"]}
```

**State read**  
`selected_article_codes`.

**State update**  
`last_comparison_codes`.

**Expected response behavior**  
Explicar diferencias verificadas.

**Forbidden behavior**  
Elegir otra lista reciente.

## CF-10 — Similarity simple

**ID**  
CF-10

**Goal**  
Descubrir alternativas a una referencia.

**Starting context**  
Ninguno.

**User message**  
“Buscame algo parecido al 900001.”

**Expected interpretation**  
`FIND_SIMILAR`.

**Clarification required?**  
No.

**Expected capability**  
`find_similar_articles`

**Expected structured arguments**
```json
{"reference_code":"900001"}
```

**State read**  
Ninguno.

**State update**  
Referencia, request, resultados aptos/no aptos y entidades.

**Expected response behavior**  
Explicar similarity score y evaluaciones relevantes.

**Forbidden behavior**  
Usar search por atributos o calcular score localmente.

## CF-11 — Similarity con required

**ID**  
CF-11

**Goal**  
Buscar similares que cumplan condiciones obligatorias.

**Starting context**  
Ninguno.

**User message**  
“Buscame algo parecido al 900001, pero tiene que ser congelado para China.”

**Expected interpretation**  
`FIND_SIMILAR_WITH_REQUIREMENTS`; ambas condiciones son required.

**Clarification required?**  
No.

**Expected capability**  
`find_similar_articles`

**Expected structured arguments**
```json
{"reference_code":"900001","required":{"producto_destino.temperatura":"CONGELADO","producto_destino.mercado":"CHINA"}}
```

**State read**  
Metadata para validar campos required.

**State update**  
Referencia, request y resultados separados por eligibility.

**Expected response behavior**  
Priorizar ELIGIBLE; explicar incumplimientos de INELIGIBLE.

**Forbidden behavior**  
Recomendar el mayor score sin considerar eligibility.

## CF-12 — Similarity sin candidatos aptos

**ID**  
CF-12

**Goal**  
Responder fielmente cuando nadie cumple required.

**Starting context**  
Solicitud similar a `900001`, mercado `CHINA` y presentación `CON_HUESO` obligatorios.

**User message**  
“¿Cuál sirve?”

**Expected interpretation**  
Explicar el resultado vigente de similarity.

**Clarification required?**  
No.

**Expected capability**  
`find_similar_articles` si aún no se ejecutó; de lo contrario explicar su respuesta vigente.

**Expected structured arguments**  
Referencia y required del contexto, sin alterarlos.

**State read**  
`last_similarity_request` y resultados.

**State update**  
Resultados actuales si se reconsulta.

**Expected response behavior**  
Decir que no existen candidatos ELIGIBLE; mostrar descartados solo como referencia.

**Forbidden behavior**  
Ascender el candidato de mayor score a apto.

## CF-13 — Búsqueda por null

**ID**  
CF-13

**Goal**  
Encontrar artículos sin código INAC.

**Starting context**  
Ninguno.

**User message**  
“¿Qué artículos no tienen código INAC?”

**Expected interpretation**  
`SEARCH_ARTICLES` con ausencia, no texto vacío.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**
```json
{"filters":[{"field":"codigos_asociaciones.codigo_inac","operator":"is_null"}]}
```

**State read**  
Metadata.

**State update**  
Búsqueda y resultados.

**Expected response behavior**  
Mostrar ausencia como criterio interpretado.

**Forbidden behavior**  
Usar `eq: null`, cadena vacía o inventar códigos.

## CF-14 — Rango numérico

**ID**  
CF-14

**Goal**  
Buscar vida útil mínima.

**Starting context**  
Ninguno.

**User message**  
“Buscame artículos con vida útil de al menos 395 días.”

**Expected interpretation**  
`SEARCH_ARTICLES`; `gte 395` días.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**
```json
{"filters":[{"field":"producto_destino.vida_util","operator":"gte","value":395}]}
```

**State read**  
Metadata de tipo y unidad.

**State update**  
Búsqueda y resultados.

**Expected response behavior**  
Indicar umbral y que el dato es sintético, no recomendación oficial.

**Forbidden behavior**  
Interpretar 395 como peso u otra unidad.

## CF-15 — Guardar filtro

**ID**  
CF-15

**Goal**  
Persistir criterios actuales.

**Starting context**  
`current_search` filtra `CHINA` y `CONGELADO`; identidad provista por la app.

**User message**  
“Guardá esta búsqueda como China congelados.”

**Expected interpretation**  
`SAVE_FILTER` con el request exacto y nombre dado.

**Clarification required?**  
No.

**Expected capability**  
`save_filter`

**Expected structured arguments**  
`name = "China congelados"`; `search = current_search`.

**State read**  
`current_search`; identidad externa.

**State update**  
`last_saved_filter` con ID/nombre devueltos.

**Expected response behavior**  
Confirmar que guardó criterios, no resultados.

**Forbidden behavior**  
Reconstruir filtros desde texto o inventar identidad.

## CF-16 — Ejecutar filtro guardado

**ID**  
CF-16

**Goal**  
Obtener resultados actuales de un filtro.

**Starting context**  
Existe un filtro inequívoco “China congelados” para el usuario actual.

**User message**  
“Ejecutá China congelados.”

**Expected interpretation**  
Resolver filtro y `EXECUTE_SAVED_FILTER`.

**Clarification required?**  
No si la resolución es inequívoca.

**Expected capability**  
`execute_saved_filter` (precedido por list/get solo si es necesario resolver ID).

**Expected structured arguments**  
ID persistido del filtro e identidad externa.

**State read**  
Filtros recientes o `last_saved_filter`.

**State update**  
`current_search`, resultados actuales y `last_saved_filter`.

**Expected response behavior**  
Presentar datos reconsultados.

**Forbidden behavior**  
Presentar resultados históricos como nuevos.

## CF-17 — Ficha contextual

**ID**  
CF-17

**Goal**  
Obtener la ficha asociada al último artículo.

**Starting context**  
`last_article_code = 900001`.

**User message**  
“Mostrame su ficha.”

**Expected interpretation**  
`GET_TECHNICAL_SHEET` para `900001`.

**Clarification required?**  
No.

**Expected capability**  
`get_technical_sheet`

**Expected structured arguments**
```json
{"article_code":"900001"}
```

**State read**  
`last_article_code`.

**State update**  
`last_technical_sheet` con identificadores y metadata.

**Expected response behavior**  
Mostrar solo metadata devuelta.

**Forbidden behavior**  
Afirmar que abrió un PDF o inventar contenido de ficha.

## CF-18 — Ambigüedad real

**ID**  
CF-18

**Goal**  
Evitar actuar sobre una referencia inexistente.

**Starting context**  
No existe antecedente inequívoco.

**User message**  
“Buscame uno parecido a ese.”

**Expected interpretation**  
Intención probable de similarity, referencia ausente.

**Clarification required?**  
Sí: “¿A qué artículo te referís?”

**Expected capability**  
Ninguna hasta aclarar.

**Expected structured arguments**  
Ninguno.

**State read**  
Entidades y referencias recientes.

**State update**  
No mutar estado operativo.

**Expected response behavior**  
Pedir solo la referencia faltante.

**Forbidden behavior**  
Elegir un artículo arbitrariamente o ejecutar una tool.

## CF-19 — Sin resultados

**ID**  
CF-19

**Goal**  
Explicar una búsqueda válida con cero coincidencias.

**Starting context**  
Una búsqueda estructurada fue ejecutada y devolvió total 0.

**User message**  
Solicitud de búsqueda correspondiente.

**Expected interpretation**  
Resultado vacío verificado, no error.

**Clarification required?**  
No.

**Expected capability**  
`search_articles`

**Expected structured arguments**  
Los criterios expresados, sin flexibilización automática.

**State read**  
Metadata y búsqueda.

**State update**  
Conservar `current_search`; resultados vacíos.

**Expected response behavior**  
Decir 0 resultados, mostrar criterios y sugerir opcionalmente uno a relajar.

**Forbidden behavior**  
Inventar alternativas o ejecutar otra búsqueda sin permiso.

## CF-20 — Error de API

**ID**  
CF-20

**Goal**  
Responder de forma segura ante indisponibilidad.

**Starting context**  
La capability/API falla o no está disponible.

**User message**  
Cualquier consulta que requiere datos actuales.

**Expected interpretation**  
La operación no pudo completarse; no hay resultado verificable.

**Clarification required?**  
No, salvo que el error indique argumentos ambiguos/corregibles.

**Expected capability**  
La correspondiente a la intención, con fallo reportado.

**Expected structured arguments**  
Los argumentos interpretados originalmente.

**State read**  
Contexto requerido para la operación.

**State update**  
No escribir resultados exitosos ni reemplazar snapshots vigentes como si fueran actuales.

**Expected response behavior**  
Informar que no pudo completar la consulta y permitir reintento.

**Forbidden behavior**  
Inventar datos o reutilizar datos anteriores como respuesta actual.
