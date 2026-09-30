# Menú de filtros guardados (Etapa 6D)

## Carencia de contrato detectada antes del cambio

La Application API V1 exponía los filtros sólo como `SAVED_FILTER_LIST` dentro de mensajes persistidos, después de pedirle al agente que los enumerara. No había una lectura autenticada que permitiera abrir un menú desde `/chat` sin crear una conversación vacía ni consumir una ejecución del modelo. El navegador tampoco debe llamar directamente a Catalog API, porque la identidad de catálogo se resuelve en el servidor.

Se agrega **sólo** `GET /api/v1/saved-filters`, con respuesta `SavedFilterListPayload` ya existente (`{ "filters": SavedFilterView[] }`). Requiere la misma cookie y utiliza `catalog_demo_user_id` del usuario autenticado. No se modifica ningún contrato 6B previo ni la semántica de búsqueda o ejecución. Los errores del catálogo se propagan como errores seguros de Application API.

La ejecución de un filtro seleccionado usa el envío conversacional existente con su ID exacto, conservando `clientMessageId`, el historial y `ARTICLE_SEARCH_RESULTS`; el frontend no recompone criterios ni calcula resultados.

## Interacción

El botón «Filtros» abre el menú. Escribir `/` al inicio de un composer vacío abre el mismo menú; `/texto` filtra localmente la lista ya cargada. Una barra dentro de una frase normal se conserva como texto. Las flechas suben/bajan, Enter selecciona y Escape cierra. Si no hay filtros, se muestra un estado vacío real. La selección envía una instrucción con el ID exacto a la conversación actual, creando una conversación sólo si se envía desde `/chat`.
