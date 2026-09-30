# Filtros guardados

Las herramientas cubren guardar, listar, consultar, ejecutar y eliminar filtros
en `/api/v1/saved-filters`. La identidad se toma de `ToolContext.user_id` y se
transmite en `X-Demo-User-Id`; nunca es un parámetro visible para el modelo. La
API aplica propiedad en cada operación.

`save_filter` guarda exactamente `current_search`; no reconstruye criterios
desde texto. Sin búsqueda previa pide realizarla. Para nombres, el agente lista y
resuelve un único ID; ante ambigüedad solicita aclaración. Ejecutar restaura la
búsqueda y el orden de resultados. Eliminar borra sólo la consulta guardada,
nunca artículos.

