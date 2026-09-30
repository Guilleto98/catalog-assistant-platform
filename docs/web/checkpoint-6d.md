# Checkpoint 6D — Catálogo · Asistente

La Etapa 6D refina la aplicación Angular de 6C sin cambiar el contrato conversacional ni implementar funciones de 6E.

| Punto solicitado | Resultado |
|---|---|
| 1. Cambios visuales | Superficies claras, verde bosque, bordes suaves, whitespace y ancho de lectura. |
| 2. Logo | SVG AgroLink original copiado intacto desde `Documents` a `apps/web/public/brand`; login, sidebar, bienvenida, asistente y favicon. |
| 3. Tokens | Colores semánticos, radios, sombra y espaciado base en `styles.scss`. |
| 4. Login | Conserva split desktop y formulario prioritario en móvil. |
| 5. Sidebar | Conversaciones, usuario, logout y nueva conversación; sin secciones pesadas. |
| 6. Collapse | Desktop colapsa a 74 px y conserva nuevo/expandir. |
| 7. Empty chat | `/chat` tiene bienvenida, sugerencias y composer utilizable. |
| 8. Lazy creation | Primer envío crea una sola conversación, navega y envía el mismo texto. Errores conservan texto; retry de navegación reutiliza ID. |
| 9. Composer | Sticky, ancho legible, Enter/Shift+Enter, adjunto deshabilitado con etiqueta, sin micrófono falso. |
| 10. Filtros button | Acción visible junto al envío. |
| 11. Slash | `/` inicial abre menú; `/texto` filtra; slash dentro de frase no lo abre. |
| 12. Menú | Un componente para botón y slash, DTOs reales, estado vacío/error, flechas, Enter y Escape. |
| 13. Ejecución | Selección envía el ID exacto por el contrato de mensajes; se observó `ARTICLE_SEARCH_RESULTS` real. |
| 14. Search results | Cards numeradas con código, nombre, corte, mercado, temperatura y presentación disponible. |
| 15. Detail | Grupos reales con secciones secundarias colapsadas. |
| 16. Comparison | Matriz con texto «Igual»/«Diferente» y scroll horizontal. |
| 17. Similarity | «Apto/No apto» prima sobre score; criterios desplegables y razones obligatorias visibles. |
| 18. Technical sheet | Metadata sin botón falso de descarga. |
| 19. Request draft | Estados traducidos y procedencia PDF/XLSX/usuario sin IDs internos. |
| 20. Responsive | Sidebar drawer móvil y composer visible; desktop/tablet conservan estructura. |
| 21. Accesibilidad | Focus visible, etiquetas, texto además de color, navegación de menú y soporte reduce-motion. |
| 22. Tests agregados | Lazy creation/retry, lectura autenticada de filtros, menú, renderers y sesión. |
| 23. Total tests | 52 frontend y 120 backend (suite sin integración/smoke). |
| 24. Build | Angular producción aprobado. |
| 25. Real smoke | Login, búsqueda, detalle, comparación, similitud, fuera de dominio, logout y expiración aprobados. |
| 26. Filter smoke | Guardado, menú con filtro real y ejecución aprobados sobre catálogo temporal. |
| 27. Refresh | Historial y UiEvents reconstruidos sin nueva ejecución del modelo. |
| 28. Screenshots | `output/playwright/6d-*.png`; se preservaron las capturas 6C. |
| 29. Regresiones | 40 pruebas previas siguen pasando; smoke 6C adaptado al nuevo contrato UX. |
| 30. Deuda técnica | El texto libre del agente se muestra como texto seguro (sin Markdown enriquecido); no hay sistema de toasts independiente. En una pasada apareció un `ERROR` parcial junto con similitud válida; en la última pasada sólo hubo `SIMILARITY_RESULTS` y ambas tools terminaron `COMPLETED`. Conviene vigilar estos eventos mixtos en auditoría. |
| 31. Siguientes pasos | Validar con usuarios la jerarquía y accesibilidad; después planificar uploads y audio en una etapa separada. |

## Cambio aditivo de contrato

`GET /api/v1/saved-filters` resuelve una carencia funcional: el menú necesita leer filtros sin crear mensajes. Exige cookie, toma la identidad de catálogo del usuario autenticado en servidor y devuelve `SavedFilterListPayload` ya existente. No hay acceso directo desde Angular a Catalog API. El motivo y la interacción están en [saved-filter-command-menu.md](saved-filter-command-menu.md).

## Aislamiento del smoke

El runner inicia Catalog API en 3001 con SQLite temporal, Application API en 3101 con bases temporales y navegador sobre el frontend local 4200. Se conserva la clave OpenAI sólo en el proceso backend. Ningún filtro del usuario local o catálogo existente se modifica por la prueba. Los procesos temporales se detienen al salir.
