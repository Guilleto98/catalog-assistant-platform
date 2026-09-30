# Matriz intent → capability

Los nombres son conceptuales y no constituyen contratos de tools. La identidad demo siempre proviene de la aplicación, nunca del modelo.

| Intent | Capability | When to use | When not to use | Required context | State read | State written | Clarification conditions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Buscar por atributos | `search_articles` | El usuario describe condiciones del resultado | Si pide alternativas respecto de una referencia | Al menos un criterio válido; una búsqueda vacía solo si el usuario pide todo el catálogo | Metadata cuando haya duda | `current_search`, resultados, entidades | Valor/campo no mapeable con seguridad |
| Refinar búsqueda | `search_articles` | Agregar, reemplazar o quitar criterios actuales | Si no existe una búsqueda aplicable y la frase aislada no es suficiente | `current_search` | Búsqueda actual | Búsqueda y resultados nuevos | Varios contextos de búsqueda plausibles |
| Consultar artículo | `get_article` | Código o referencia singular inequívoca | Para comparar o descubrir alternativas | Código resuelto | Resultados/entidades recientes | `last_article_code`, entidades | Pronombre u ordinal sin antecedente |
| Comparar artículos | `compare_articles` | Explicar diferencias entre 2–10 artículos identificados | Para buscar otros similares | 2–10 códigos | Selección, resultados o menciones | `last_comparison_codes` | Menos de 2 o conjunto ambiguo |
| Buscar alternativas | `find_similar_articles` | Hay referencia y se buscan artículos parecidos | Una búsqueda meramente multiatributo | Exactamente `reference_code` o features | Artículo/selección reciente | Referencia, request y resultados | Sin referencia; referencia ambigua |
| Alternativas con requisitos | `find_similar_articles` | Similarity con obligatoriedad lingüística clara | Preferencias blandas o campos no permitidos como required | Referencia/features y required válidos | Referencia, metadata | Request y resultados por eligibility | Preferencia vs requisito cambia materialmente el resultado |
| Obtener ficha | `get_technical_sheet` | Se pide ficha por artículo/ficha inequívoca | Para inventar PDF o contenido no devuelto | Código o ficha resueltos | Artículo, selección o ficha reciente | `last_technical_sheet` | Referencia ambigua |
| Guardar búsqueda | `save_filter` | Hay `current_search` y nombre suficiente | Para guardar resultados o sin búsqueda actual | Búsqueda, nombre, identidad de app | `current_search` | `last_saved_filter` | Sin búsqueda; nombre faltante si la API lo requiere |
| Listar filtros | `list_saved_filters` | El usuario pide sus filtros/búsquedas guardadas | Para listar resultados del catálogo | Identidad de app | Ninguno | Entidades de filtros recientes | Identidad ausente/inválida |
| Consultar filtro | `get_saved_filter` | Se piden criterios o metadata de un filtro identificado | Para ejecutarlo implícitamente sin pedido | ID resuelto e identidad | Filtros recientes | `last_saved_filter` | Nombre ambiguo o no resuelto |
| Ejecutar filtro | `execute_saved_filter` | Se solicitan resultados actuales de un filtro | Para mostrar un snapshot viejo | ID resuelto e identidad | Filtros recientes/`last_saved_filter` | `current_search`, resultados, filtro | Nombre ambiguo o inexistente |
| Borrar filtro | `delete_saved_filter` | Se solicita eliminar un filtro inequívoco | Para borrar búsqueda actual o datos del catálogo | ID resuelto e identidad | Filtros recientes/`last_saved_filter` | Limpia referencia eliminada | Nombre ambiguo; futuras políticas podrían exigir confirmación |
| Aclarar | Ninguna | La ambigüedad cambia materialmente operación/argumentos | Para completar detalles opcionales | Pregunta mínima | Contexto relevante | No muta operación | No aplica |

## Reglas transversales

- Search usa operadores admitidos por metadata: `eq`, `neq`, `in`, `contains`, `gte`, `lte`, `between`, `is_null`, según el campo.
- Compare requiere 2–10 códigos.
- Similarity admite exactamente una referencia: código o features; `limit` es 1–10.
- `required` es independiente de features ponderadas y se valida en la API.
- Save guarda `current_search` estructurado, no una reconstrucción desde texto ni los resultados.
- Execute vuelve a consultar datos actuales y respeta ownership.
- Los errores de API no habilitan fallbacks inventados ni uso de snapshots como datos actuales.
