# Etapa 6C — Angular Foundation

Aplicación real en `apps/web`: login, restauración de sesión, sidebar, conversaciones,
historial y mensajes contra Application API V1. No depende de ADK Web.

## Versiones y decisiones

Angular/CLI 22.2, Node instalado 26.10.0, npm 11.19.1, TypeScript 6.0.
Node 26 está dentro del rango compatible documentado por
[Angular](https://angular.dev/reference/versions); las versiones exactas se fijan en
`apps/web/package-lock.json`. No se actualizaron los otros proyectos ni Node global.

Standalone, Router, HttpClient, signals y `computed`; TypeScript `strict` y templates
estrictos explícitos. SCSS sin librerías UI, sin NgRx, fuentes del sistema, tema claro,
tokens pequeños y marca provisional «Catálogo · Asistente». Sin recursos externos.

## Estructura y estado

```text
src/app/
  api/contracts.ts                 aliases del contrato público
  api/generated/application-api.ts OpenAPI → TypeScript; no editar
  core/api/                        configuración, errores, interceptor
  core/auth/                       AuthService, guards, invalidación
  features/login/                  formulario
  features/chat/services/          API wrapper + SidebarStore + ChatStore
  features/chat/pages/             shell y navegación
  features/chat/components/        composer, sidebar, mensajes, eventos
  testing/                         fixtures sólo para tests
```

AuthService es dueño de usuario/sesión. SidebarStore administra lista/paginación y
creación. ChatStore administra conversación activa/historial/envío y reconciliación.
Cada uno tiene errores propios. Revisiones de carga evitan que respuestas tardías de
otra conversación o sesión vuelvan a poblar la pantalla. No replica state ADK.

## Contratos y configuración

Fuente: `docs/contracts/application-api-v1.openapi.json`, no modelos internos Python.
Generación reproducible `npm run web:contracts`: openapi-typescript 7.13.0 en entorno
npx aislado con TypeScript 5.9.3. Su peer dependency aún no acepta TS6; **no** se
degradó Angular ni se instaló con `--force`. Los tipos generados se consumen desde TS6.
Fixtures de tests se regeneran desde ejemplos públicos en `pretest`.

`apps/web/public/config.json` contiene únicamente:

```json
{"apiBaseUrl":"http://localhost:3100/api/v1"}
```

Se carga antes del bootstrap; `API_BASE_URL` se inyecta centralmente. Puede sustituirse
al desplegar sin recompilar. Nunca colocar claves, password o cookies en config.
URLs mal formadas/protocolos extraños fallan con mensaje seguro. El hosting debe
evitar cachear config y reescribir rutas del Router a `index.html`.

Se usa conexión directa, **sin proxy de desarrollo**: ejercita CORS real. Navegador y
API comparten hostname `localhost`; no mezclar con `127.0.0.1`. Backend:
`FRONTEND_ORIGIN=http://localhost:4200`, credentials habilitadas, sin wildcard.

## Auth y rutas

Al arrancar se espera GET `/auth/me`: sesión/loading → usuario o guest; si API no
responde, pantalla recuperable con retry. No hay flash de datos privados.
Login POST email/password y confirma usuario con GET `/auth/me`. Password sólo vive
en formulario y se limpia después del envío; no se persiste ni se loguea.
Interceptor agrega `withCredentials:true` exclusivamente al API base configurado.
Cookie HttpOnly; nunca se lee ni se guarda token en local/sessionStorage.

`/login`: guest guard; `/chat`, `/chat/:conversationId`: auth guard que espera sesión.
Raíz y rutas desconocidas redirigen a chat y luego según auth. Admin puede usar shell
sin navegación `/admin`. El backend siempre autoriza; guards no sustituyen permisos.

401 de peticiones protegidas invalida sesión, limpia stores y navega a login; login y
startup excluyen 401 esperado para evitar loops. 403 muestra error, no cierra sesión.
Logout POST revoca cookie y limpia UI. Si falla por conexión, se avisa en login que
la revocación no está confirmada y se ofrece reintentar; no se afirma cierre remoto.

## Conversaciones y envíos

Sidebar respeta orden del backend; primera página20, botón «Ver más»; título/preview/
fecha provienen de API. POST `/conversations` crea y navega por ID.
Abrir/direct URL: GET metadata + mensajes paginados100 ASC; carga páginas hasta total,
sin ejecutar agente. ARCHIVED permite lectura y bloquea composer. 404 no revela dueño.

Composer multiline, Enter envía, Shift+Enter salto, composición IME respetada,
máximo20000; deshabilitado en envío. Muestra usuario optimista separado del MessageDto,
«Pensando…» y luego usa userMessage/assistantMessage retornados, deduplicando por ID.
Respuesta actual es síncrona, sin SSE ni streaming.

UUID generado una sola vez por intención. Retry conserva ID, texto y attachmentIds.
Ante falla HTTP consulta historial porque USER/run podrían estar persistidos; mantiene
texto pendiente sin fabricar assistant. Run STARTED conserva pendiente; FAILED explica
que consultar no reejecuta. «Liberar envío y volver al chat» reconcilia historial antes
de una nueva intención/UUID; ninguna reejecución automática. Pendientes viven sólo en
memoria por conversación hasta logout; el refresh recupera sólo datos persistidos.

Sidebar se refresca tras respuesta para título/preview nuevos. Historial no se vuelve
a solicitar después de un envío exitoso. Al abrir se baja al final; nuevas respuestas
siguen al final sólo si usuario no se desplazó a mensajes anteriores.

## Mensajes y UiEvents

Texto renderizado con interpolación Angular y `white-space:pre-wrap`. Markdown puede
aparecer como texto literal: decisión deliberada para esta fundación; no usa innerHTML,
`bypassSecurityTrustHtml`, HTML arbitrario ni links/media externas. Formato Markdown
limitado y seguro queda para6D. Narrativa no se usa para reconstruir datos.

UiEventRenderer valida schemaVersion1 y despacha unión discriminada fuera del chat:

| Tipo | Vista básica |
|---|---|
| ARTICLE_SEARCH_RESULTS | total, código, nombre, corte, mercado, temperatura |
| ARTICLE_DETAIL | grupos/fields determinísticos, secciones plegables |
| ARTICLE_COMPARISON | tabla y SAME/DIFFERENT del payload, sin recalcular |
| SIMILARITY_RESULTS | secciones Aptos/No aptos, código, score, eligibility |
| TECHNICAL_SHEET | metadata, sin descarga PDF inventada |
| REQUEST_DRAFT | valores/status/required, sólo lectura |
| SAVED_FILTER_LIST/CREATED/DELETED | lista/nombre/confirmación |
| ATTACHMENT_STATUS | nombre/tipo/estado/error seguro |
| ERROR | mensaje conversacional seguro |

Eventos ordenados por sequence; tipo/versión desconocidos tienen fallback sin adivinar
schema ni mostrar JSON técnico. Todos los valores se escapan, incluso catálogo y
documentos no confiables. 90 INELIGIBLE no se presenta como alternativa apta al70
ELIGIBLE. Datos de tarjetas siguen siendo snapshots de la ejecución.

## UX y accesibilidad

Desktop/sidebar fija; tablet más compacta; móvil menú lateral con overlay, sin overflow
horizontal de página (tablas desplazan internamente). Labels, botones semánticos,
aria-current, nombres accesibles, focus visible, loading `role=status`, errores
`role=alert`, idioma español y reduced-motion. No auditoría WCAG completa aún.

## Comandos locales

Una vez: `npm run web:install`. API/agent ya instalados y credencial sólo en backend.

```bash
# Terminal 1: catálogo existente, sin reset/reseed
npm run api:dev
# Terminal 2: Application API
npm run agent:api
# Terminal 3: Angular
npm run web:dev
```

Abrir `http://localhost:4200` e ingresar con usuario creado en el bootstrap6A.
Para una instancia local vacía, `npm run agent:demo:login` crea
`demo.local@solvo.test`, CLIENT_USER en «Pruebas locales», con contraseña aleatoria
guardada en `apps/agent/var/local-login.txt` (permisos0600, ignorada por Git). No la
publica en stdout ni en el frontend; el script no resetea contraseñas existentes.
No hay registro público. Ver `docs/platform/identity.md` para bootstrap seguro.
No levantar dos procesos sobre3000/3100/4200. ADK Web es opcional sólo para debug.

Si el catálogo está inicializado en Docker: `npm run api:docker:refresh` usa overlay
`docker-compose.preserve.yml` y omite seed destructivo; mantiene volumen y ejecuta
migraciones. El arranque original `api:docker:up` sí vuelve a sembrar y puede borrar
filtros: no usarlo para conservar datos existentes. Docker Hub falló al actualizar
en esta ejecución; el smoke utiliza el código actual compilado y ejecutado localmente
en3000. No se alteró código funcional de catálogo ni sus datos.

```bash
npm run web:contracts
npm run web:test
npm run web:lint
npm run web:build
# smoke real requiere3000+4200; API temporal3101, no usa base3100
npm run web:smoke
```

`web:lint` verifica Prettier; el build es la validación estricta TS/templates. No se
agregó otro stack de lint. Smoke requiere navegador Chromium instalado con
`npm exec --prefix apps/web -- playwright install chromium`; hace llamadas pagas al
proveedor autorizado, sin retry automático del test. Usa cuenta, contraseña aleatoria
y bases temporales, no modifica usuarios/conversaciones de la app. El navegador jamás
recibe OPENAI_API_KEY. Intercepta únicamente config pública para usar3101; no mocks de
respuestas. Simula backend no disponible abortando conexión y expira sesiones únicamente
en DB temporal. Capturas y resultado seguro: `output/playwright/6c-*`.

## Límite de esta etapa

No upload/mic, draft editing, saved filters panel, Admin UI, creación, clonación,
mutaciones, RAG, multi-agent ni streaming. Scope FAIL_OPEN no se cambió.
La auditoría del contenido del modelo sigue necesitando evals/contraste con herramientas;
una UI correcta no convierte narrativa en garantía100% ni certifica producción.
Rich UI/Markdown/adjuntos para6D; Admin/Audit para6E. STOP al terminar6C.
