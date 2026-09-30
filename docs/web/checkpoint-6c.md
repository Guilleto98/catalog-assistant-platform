# Entrega Etapa 6C

Fecha: 30 septiembre2026. Implementación en `apps/web`; backend funcional reutilizado,
sin cambios a tools, contratos, auth ni Domain Scope. Detalle de arquitectura y comandos
en [angular-foundation.md](angular-foundation.md).

## Los 39 puntos solicitados

1. **Versión:** Angular/core y CLI22.2.0; TS6.0.3, Node26.10.0, npm11.19.1.
2. **Estructura:** api/generated, core/api, core/auth, features/login,
   features/chat/{services,pages,components/events}, testing y e2e.
3. **UI:** ninguna librería de componentes ni recursos externos.
4. **CSS:** SCSS, tokens chicos, claro/neutro, fuente sistema, marca provisional.
5. **State:** signals/computed; AuthService, SidebarStore y ChatStore separados.
6. **API client:** HttpClient wrapper tipado, interceptor credentials y errores seguros.
7. **Tipos OpenAPI:** generados con openapi-typescript7.13.0; aliases propios; regenerables.
   Generador aislado con TS5.9 para no forzar su peer incompatible con TS6.
8. **Base URL:** public/config.json → InjectionToken API_BASE_URL; localhost3100/api/v1.
9. **AuthService:** login, logout, loadCurrentUser, usuario nullable, estados loading/ready/
   unavailable, manejo de invalidación; auth/me fuente de verdad.
10. **Cookie:** withCredentials central, HttpOnly/SameSiteLax del backend; no JWT en storage.
11. **Guards:** auth espera verificación; guest redirige usuario verificado.
12. **Routing:** login, chat, chat/:conversationId; raíz/redirección por auth; sin admin.
13. **Login:** labels, validación, Enter, busy, error genérico, password local y limpiada;
   reintento de cierre remoto si hubo falla de red en logout.
14. **Layout:** sidebar, encabezado, historial scrollable y composer separado.
15. **Sidebar:** crear, lista activa, organización/email, badge admin pequeño y logout.
16. **Lista:** título/preview/fecha y orden backend; página20 y «Ver más».
17. **Nueva:** POST real y navegación a ID; creación protegida contra doble clic.
18. **Historial:** metadata+GET messages, paginado100 ASC hasta completar; UiEvents persistidos;
   loading/not-found/error no se confunden con conversación vacía.
19. **Composer:** multiline, Enter/ShiftEnter, IME, límite20000, disabled y «Pensando…».
20. **Idempotencia:** UUID por intención, retry mismo ID/contenido, reconciliación por ID;
   no reejecución automática de run FAILED. Pendiente conserva texto durante errores.
21. **Mensajes:** USER/ASSISTANT/SYSTEM_EVENT separados, hora local y texto escapado;
   Markdown literal por ahora, no HTML ni extracción de datos desde narrativa.
22. **UiEventRenderer:** dispatch tipado y schemaVersion1 fuera del ChatPage.
23. **Renderers:** búsqueda, detalle, comparación, similitud, ficha, draft, lista/creación/
   borrado de filtros, attachment y error; los11 no rompen el frontend.
24. **Errores:** conexión/auth/carga/envío separados;403 conserva sesión;404 genérico;
   5xx safe, sin stacks, prompts ni respuestas crudas de proveedor.
25. **Expiración:**401 central limpia usuario/sidebar/historial/pendientes y navega login;
   startup/login401 esperado no causa loops.
26. **Desconocidos:** tipo/schemaVersion desconocido muestra fallback seguro sin inferir DTO.
27. **Responsive:** desktop/tablet; móvil390×844 con menú lateral/overlay y sin overflow
   horizontal de página. No optimización exhaustiva móvil aún.
28. **Accesibilidad:** labels, botones semánticos, aria-current/nombres, focus visible,
   status/alert, idiomaes y reduced-motion. No certificación WCAG.
29. **Tests:** AuthService/guards/interceptor, login, API/lista/creación/historial/paginación,
   envío/UUID/retry/FAILED/races/logout-state, composer,11 renderers, unknown/version,
   aptitud crítica, XSS y ficha sin fake download; Playwright real aparte.
30. **Total:**40 unitarios frontend +1 smoke de navegador completo. Backend:119 unitarios,
   2 integración catálogo,5 unitarios catálogo,17 e2e catálogo;5 smokes live existentes
   omitidos por flags, no contabilizados como aprobados.
31. **Build:** producción estricto aprobado; aproximadamente289kB inicial /79kB transferido
   estimado, chat/login lazy, sin dependencias UI pesadas. Prettier aprobado.
32. **Smoke real:** cookie login→sidebar→create→bifeChina→detalleprimero→similar900001 con
   China obligatorio→out-of-domain→refresh/directURL→conversaciónB→logout/expiry/offline.
   Usuario/base temporal, sin fixtures de respuestas; OpenAI real sólo en backend.
33. **Refresh:** conserva cookie, ruta, mensajes y eventos; conteos de runs/tools/UiEvents
   no aumentan por lectura. Verificación adicional de backend bloquea runtime/outbound
   en sus tests de lectura. No llamada para reconstruir historial.
34. **Aislamiento:** A busca bifeChina; B «Solo los deChina» no hereda BIFE_ANCHO en tools;
   frontend usa ID de ruta y descarta respuestas tardías de otra conversación.
35. **Similarity:** Aptos/No aptos separados;900006 ELIGIBLE y900004 INELIGIBLE en secciones
   diferentes. Test unitario fija70/90; payload real respeta aptitud, no umbral UI.
36. **Seguridad:** cookie HttpOnly verificada por browser; JS no la lee, storage vacío,
   ninguna petición directa a Catalog/OpenAI/ADK, output no confiable escapado; no
   credenciales en config/bundle y cero errores no controlados de página en smoke.
37. **Deuda:** Markdown literal; historial completo en memoria sin virtualización;
   pendientes inciertos no sobreviven refresh (sí USER/run persistidos); sin archive UI,
   adjuntos, draft review, admin ni streaming. Backend8h absolutas sin refresh/idle,
   Secure false sólo local, rate-limits/MFA/CSP/producción requieren trabajo separado.
   FAIL_OPEN se preserva. Sin promesa de corrección100% del texto libre del LLM.
38. **Visual:** [login](../../output/playwright/6c-login.png),
   [búsqueda](../../output/playwright/6c-chat-search.png),
   [detalle](../../output/playwright/6c-chat-detail.png),
   [similitud](../../output/playwright/6c-similarity.png),
   [móvil](../../output/playwright/6c-mobile.png).
39. **6D:** mejorar cards/detalle/comparación/criterios, Markdown seguro limitado,
   draft review y adjuntos/audio, conservando contratos y tests de confianza.
   No se inició automáticamente.

## Evidencia y límites operativos

Resultado seguro: [6c-smoke-result.json](../../output/playwright/6c-smoke-result.json).
Pruebas no guardan trazas/video ni passwords; cuenta de prueba y bases se eliminan
al finalizar. No se modificaron conversaciones/usuarios de la instancia3100.

La primera prueba de navegador falló por un selector exacto que no incluía el símbolo
«＋» del botón, no por el backend. Se agregó nombre accesible explícito y pasó el
recorrido. Inspección visual encontró scroll programado antes del render; se usa
afterNextRender y se comprueba desplazamiento al final en smoke. Ajustes no afectan
contenido del agente ni autoridad de catálogo.

Docker Hub agotó plazo al descargar node22-alpine. No se reseedó ni borró volumen.
Catálogo actual fue compilado y levantado localmente en3000, health50 artículos;
integración y17 e2e aprobaron. Se agregó overlay de actualización sin seed destructivo
para cuando Docker Hub vuelva a estar disponible. No se afirma rebuild Docker exitoso.

Servicios de uso quedan en3000 (catalog),3100 (Application API existente) y4200
(Angular). Smoke3101 finaliza y borra sólo su directorio temporal. Sin cuentas default
ni passwords publicadas. Entrar con tu usuario provisionado en6A.

**STOP6C.** Sin mutaciones, creación/clonación, RAG, multi-agent, admin completo ni streaming.
