# Escenarios conversacionales V1

Especificación para futuros evals; no contiene tests ejecutables ni exige coincidencia literal del mensaje. Paráfrasis semánticamente equivalentes deben producir el mismo comportamiento.

## EV-01 — Búsqueda simple

- **scenario_id:** `EV-01`
- **conversation:** Usuario: “Buscame bife ancho.”
- **expected_intent:** `SEARCH_ARTICLES`
- **expected_capability:** `search_articles`
- **expected_arguments:** filtro `producto_destino.corte eq BIFE_ANCHO`
- **expected_state_before:** sin requisitos
- **expected_state_after:** `current_search` y resultados actualizados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** criterios y resultados provienen de metadata/API
- **forbidden_behavior:** preguntar obligatoriamente mercado o usar similarity

## EV-02 — Búsqueda múltiple

- **scenario_id:** `EV-02`
- **conversation:** Usuario: “Necesito bife ancho congelado destinado a China.”
- **expected_intent:** `SEARCH_ARTICLES`
- **expected_capability:** `search_articles`
- **expected_arguments:** filtros `corte eq BIFE_ANCHO`, `temperatura eq CONGELADO`, `mercado eq CHINA`
- **expected_state_before:** cualquiera; solicitud autosuficiente
- **expected_state_after:** reemplaza `current_search`; guarda resultados ordenados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** la API determina coincidencias
- **forbidden_behavior:** convertir atributos en similarity o required

## EV-03 — Refinamiento

- **scenario_id:** `EV-03`
- **conversation:** Búsqueda vigente `corte=BIFE_ANCHO`; usuario: “Solo los del mercado chino.”
- **expected_intent:** `SEARCH_ARTICLES` por refinamiento
- **expected_capability:** `search_articles`
- **expected_arguments:** conserva corte; agrega `mercado eq CHINA`; `page=1`
- **expected_state_before:** `current_search` con corte
- **expected_state_after:** búsqueda combinada y resultados nuevos
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** reejecuta la API
- **forbidden_behavior:** olvidar corte o responder desde resultados anteriores

## EV-04 — Reemplazo

- **scenario_id:** `EV-04`
- **conversation:** Búsqueda vigente con `mercado=CHINA`; usuario: “No, mejor Brasil.”
- **expected_intent:** `SEARCH_ARTICLES` con corrección
- **expected_capability:** `search_articles`
- **expected_arguments:** `mercado eq BRASIL`, sin `CHINA`; demás criterios intactos
- **expected_state_before:** mercado China
- **expected_state_after:** mercado Brasil y resultados reconsultados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** la nueva respuesta proviene de API
- **forbidden_behavior:** `in [CHINA, BRASIL]`

## EV-05 — Eliminar condición

- **scenario_id:** `EV-05`
- **conversation:** Búsqueda vigente con temperatura; usuario: “Me da igual la temperatura.”
- **expected_intent:** `SEARCH_ARTICLES` con REMOVE
- **expected_capability:** `search_articles`
- **expected_arguments:** request anterior sin `producto_destino.temperatura`
- **expected_state_before:** temperatura presente
- **expected_state_after:** temperatura ausente; otros criterios preservados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** resultados nuevos de API
- **forbidden_behavior:** mantener o sustituir la temperatura

## EV-06 — Detalle explícito

- **scenario_id:** `EV-06`
- **conversation:** Usuario: “¿Qué datos tiene el 900001?”
- **expected_intent:** `GET_ARTICLE`
- **expected_capability:** `get_article`
- **expected_arguments:** `codigo=900001`
- **expected_state_before:** ninguno
- **expected_state_after:** `last_article_code=900001`
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** detalle consultado en API
- **forbidden_behavior:** inventar atributos ausentes

## EV-07 — Ordinal

- **scenario_id:** `EV-07`
- **conversation:** Lista visible `[900001,900004,900006]`; usuario: “Abrí el segundo.”
- **expected_intent:** `GET_ARTICLE`
- **expected_capability:** `get_article`
- **expected_arguments:** `codigo=900004`
- **expected_state_before:** resultados en ese orden
- **expected_state_after:** `last_article_code=900004`
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** resolver orden y reconsultar detalle
- **forbidden_behavior:** usar otro conjunto o snapshot como detalle actual

## EV-08 — Comparación explícita

- **scenario_id:** `EV-08`
- **conversation:** Usuario: “¿Qué cambia entre 900001, 900002 y 900003?”
- **expected_intent:** `COMPARE_ARTICLES`
- **expected_capability:** `compare_articles`
- **expected_arguments:** `codes=[900001,900002,900003]`
- **expected_state_before:** ninguno
- **expected_state_after:** mismos códigos en `last_comparison_codes`
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** usar diferencias de API; benchmark: 15 campos diferentes y 6 iguales
- **forbidden_behavior:** comparar mediante conocimiento del modelo

## EV-09 — Comparación contextual

- **scenario_id:** `EV-09`
- **conversation:** Selección `[900001,900004]`; usuario: “Compará esos dos.”
- **expected_intent:** `COMPARE_ARTICLES`
- **expected_capability:** `compare_articles`
- **expected_arguments:** `codes=[900001,900004]`
- **expected_state_before:** selección inequívoca
- **expected_state_after:** `last_comparison_codes` actualizado
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** diferencias provienen de API
- **forbidden_behavior:** seleccionar otros artículos

## EV-10 — Similarity simple

- **scenario_id:** `EV-10`
- **conversation:** Usuario: “¿Hay alternativas parecidas al 900001?”
- **expected_intent:** `FIND_SIMILAR`
- **expected_capability:** `find_similar_articles`
- **expected_arguments:** `reference_code=900001`, sin `features`
- **expected_state_before:** ninguno
- **expected_state_after:** referencia, request y resultados separados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** scores y evaluaciones vienen de API
- **forbidden_behavior:** calcular score o enviar referencia y features juntos

## EV-11 — Similarity con requisitos

- **scenario_id:** `EV-11`
- **conversation:** Usuario: “Algo parecido al 900001, pero sí o sí congelado y para China.”
- **expected_intent:** `FIND_SIMILAR_WITH_REQUIREMENTS`
- **expected_capability:** `find_similar_articles`
- **expected_arguments:** referencia `900001`; required temperatura `CONGELADO` y mercado `CHINA`
- **expected_state_before:** ninguno
- **expected_state_after:** request y listas por eligibility
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** benchmark: `900004` score 90 es INELIGIBLE; `900006` score 70 es ELIGIBLE
- **forbidden_behavior:** recomendar `900004` como apto

## EV-12 — Ningún candidato apto

- **scenario_id:** `EV-12`
- **conversation:** Usuario pide similar a `900001`, obligatoriamente `CHINA` y `CON_HUESO`
- **expected_intent:** `FIND_SIMILAR_WITH_REQUIREMENTS`
- **expected_capability:** `find_similar_articles`
- **expected_arguments:** required mercado `CHINA`, presentación `CON_HUESO`
- **expected_state_before:** ninguno
- **expected_state_after:** `eligible_candidates=[]`; conserva ineligible como descartados
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** informar ausencia de aptos y razones API
- **forbidden_behavior:** promover el mayor score

## EV-13 — Campo nulo

- **scenario_id:** `EV-13`
- **conversation:** Usuario: “Mostrame los que no tienen código INAC.”
- **expected_intent:** `SEARCH_ARTICLES`
- **expected_capability:** `search_articles`
- **expected_arguments:** `codigos_asociaciones.codigo_inac is_null`, sin value
- **expected_state_before:** ninguno
- **expected_state_after:** búsqueda y resultados; benchmark total 7
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** códigos esperados `900007, 900014, 900021, 900028, 900035, 900042, 900049`
- **forbidden_behavior:** `eq null`, texto vacío o lista inventada

## EV-14 — Umbral numérico

- **scenario_id:** `EV-14`
- **conversation:** Usuario: “Vida útil de por lo menos 395 días.”
- **expected_intent:** `SEARCH_ARTICLES`
- **expected_capability:** `search_articles`
- **expected_arguments:** `producto_destino.vida_util gte 395`
- **expected_state_before:** ninguno
- **expected_state_after:** búsqueda y resultados; benchmark total 12
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** respetar unidad días y dato sintético
- **forbidden_behavior:** presentar el valor como recomendación oficial

## EV-15 — Guardar búsqueda

- **scenario_id:** `EV-15`
- **conversation:** Con búsqueda China+Congelado: “Guardala como China congelados.”
- **expected_intent:** `SAVE_FILTER`
- **expected_capability:** `save_filter`
- **expected_arguments:** `name="China congelados"`, `search=current_search` exacto
- **expected_state_before:** búsqueda actual e identidad de app
- **expected_state_after:** referencia del filtro creado
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** API valida y persiste criterios
- **forbidden_behavior:** guardar resultados, reconstruir criterios o inventar usuario

## EV-16 — Ejecutar filtro

- **scenario_id:** `EV-16`
- **conversation:** Existe filtro inequívoco; usuario: “Volvé a correr China congelados.”
- **expected_intent:** `EXECUTE_SAVED_FILTER`
- **expected_capability:** `execute_saved_filter`
- **expected_arguments:** ID resuelto e identidad externa
- **expected_state_before:** filtro reciente/listable
- **expected_state_after:** `current_search` y resultados actuales
- **expected_clarification:** ninguna si hay coincidencia única
- **expected_grounding_behavior:** vuelve a consultar API y respeta ownership
- **forbidden_behavior:** mostrar resultados guardados o cambiar identidad

## EV-17 — Ficha contextual

- **scenario_id:** `EV-17`
- **conversation:** `last_article_code=900001`; usuario: “Mostrame su ficha.”
- **expected_intent:** `GET_TECHNICAL_SHEET`
- **expected_capability:** `get_technical_sheet`
- **expected_arguments:** artículo `900001`
- **expected_state_before:** referencia singular inequívoca
- **expected_state_after:** IDs y metadata de ficha
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** presentar solo campos devueltos por API
- **forbidden_behavior:** afirmar existencia de PDF o contenido no devuelto

## EV-18 — Referencia ambigua

- **scenario_id:** `EV-18`
- **conversation:** Sin antecedente: “Buscame uno parecido a ese.”
- **expected_intent:** `CLARIFICATION` sobre posible `FIND_SIMILAR`
- **expected_capability:** ninguna
- **expected_arguments:** ninguno
- **expected_state_before:** sin referencia compatible
- **expected_state_after:** sin mutación operativa
- **expected_clarification:** “¿A qué artículo te referís?”
- **expected_grounding_behavior:** no consultar con referencia inventada
- **forbidden_behavior:** tool call o elección arbitraria

## EV-19 — Cero resultados

- **scenario_id:** `EV-19`
- **conversation:** Una búsqueda válida devuelve cero coincidencias
- **expected_intent:** `SEARCH_ARTICLES`
- **expected_capability:** `search_articles`
- **expected_arguments:** criterios originales sin cambios
- **expected_state_before:** criterios interpretados
- **expected_state_after:** conserva búsqueda; resultados vacíos
- **expected_clarification:** ninguna
- **expected_grounding_behavior:** informar cero y mostrar criterios
- **forbidden_behavior:** inventar alternativas o flexibilizar automáticamente

## EV-20 — API no disponible

- **scenario_id:** `EV-20`
- **conversation:** Usuario realiza una consulta; la API/tool no está disponible
- **expected_intent:** la correspondiente a la solicitud
- **expected_capability:** capability correcta, con fallo controlado
- **expected_arguments:** argumentos interpretados
- **expected_state_before:** contexto normal
- **expected_state_after:** no registrar resultado exitoso
- **expected_clarification:** ninguna por indisponibilidad
- **expected_grounding_behavior:** informar que no pudo completar y permitir reintento
- **forbidden_behavior:** inventar resultados o usar snapshots como actuales

## Benchmarks determinísticos reutilizados

Los siguientes datos proceden de `apps/catalog-api/docs/reference_queries.md` y deberán fijarse en futuros evals de integración:

- corte `BIFE_ANCHO` + mercado `CHINA`: `900001`, total 1;
- vida útil `gte 395`: total 12;
- código INAC `is_null`: 7 códigos enumerados en EV-13;
- comparación `900001/2/3`: 15 campos diferentes, 6 iguales;
- similarity con China+Congelado: diferencia crítica entre `900004` INELIGIBLE/90 y `900006` ELIGIBLE/70;
- similarity China+Con hueso: ningún candidato eligible.

Los evals futuros deben comprobar intención, capability, argumentos, llamadas, grounding, transición de estado y respuesta; no implementar ramas basadas en la frase exacta.
