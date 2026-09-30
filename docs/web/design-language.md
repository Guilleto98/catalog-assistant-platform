# Lenguaje de diseño del catálogo (6D)

La interfaz continúa la base Angular de 6C: acceso dividido, sidebar claro y chat de una columna. La referencia AgroLink se interpreta como una herramienta de trabajo tranquila, no como un dashboard. El SVG original se encontró en `Documents` y se copió intacto a `apps/web/public/brand/agrolink-symbol-smooth-3d.svg`; no se generó una imitación.

## Tokens

Los colores y superficies se centralizan en `apps/web/src/styles.scss`: verde principal `#396c2e` (borde del SVG), oscuro `#285c30` (tono final del gradiente), verde pálido `#edf4e9`, fondo `#fafbf9`, borde `#e0e7e2`, texto `#223833` y texto secundario `#71807b`. Se usan también tokens semánticos para éxito, advertencia y peligro. Tipografía: pila sans-serif del sistema. Radios amplios, sombra muy tenue y foco visible de tres píxeles. Las transiciones respetan `prefers-reduced-motion`.

## Estructura

- Desktop: sidebar de conversaciones y área principal con ancho de lectura máximo de 850 px. El sidebar colapsa a una banda de 74 px con acceso a expandir y nueva conversación.
- Mobile: sidebar como drawer; el composer permanece visible al pie. Las tablas de comparación conservan scroll horizontal.
- `/chat` vacío: estado de bienvenida y composer funcional. Las sugerencias son acciones reales, no respuestas fijas.

## Mensajes y eventos

El usuario se alinea a la derecha sobre verde pálido. El asistente queda a la izquierda, con texto y UiEvents persistidos. La búsqueda prioriza código, nombre, corte, mercado, temperatura y presentación, con numeración estable. El detalle agrupa campos reales y permite desplegar secciones. La comparación mantiene una matriz con «Igual»/«Diferente». La similitud separa «Aptos» y «No aptos» según `eligibility` del servidor; `score` es secundario y los criterios obligatorios no coincidentes se muestran explícitamente. El borrador traduce estados de campo y muestra procedencia sin IDs ni rutas internas. La ficha técnica nunca ofrece descarga si `documentAvailable=false`.

El frontend no calcula aptitud, puntajes, validez, filtros ni datos de catálogo: sólo interpreta DTO y enum de Application API. El indicador «Pensando…» significa solicitud en curso; no simula streaming.

## Entrada y filtros

El composer permite Enter para enviar y Shift+Enter para salto. «+» está claramente deshabilitado hasta tener UX de adjuntos; no se muestra micrófono falso. El botón «Filtros» y `/` comparten el mismo menú autenticado. Ver [menú de filtros guardados](saved-filter-command-menu.md).

## Evidencia visual

Las capturas reales se guardan bajo `output/playwright/6d-*.png`; las de 6C se preservan como línea base. El smoke usa catálogo, Application API y base de conversaciones temporales, y verifica que refrescar no vuelve a ejecutar al agente.
