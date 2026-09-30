# Angular — Asistente de artículos

Frontend real de Etapas 6C–6D. Angular22.2.0, standalone, SCSS, signals y contratos V1.
No tiene respuestas de demo ni se conecta directamente a ADK/OpenAI/Catalog API.

## Instalar y levantar

Desde la raíz del monorepo:

```bash
npm run web:install
npm run web:dev
```

Abrir `http://localhost:4200`. Requiere catálogo actualizado en3000 y Application API
en3100 (`npm run api:dev`, `npm run agent:api` en terminales distintas).
No ejecutar dos servicios sobre el mismo puerto. Para una instancia local vacía,
`npm run agent:demo:login` crea una cuenta CLIENT_USER con contraseña aleatoria en
`apps/agent/var/local-login.txt` (privada e ignorada por Git). Si ya existen
usuarios, también se puede usar el bootstrap de `../../docs/platform/identity.md`.

## Configuración pública

Editar `public/config.json`: `apiBaseUrl` por defecto `http://localhost:3100/api/v1`.
No requiere `.env` del frontend. No incluir secretos ni credenciales en ese JSON.
Backend `FRONTEND_ORIGIN=http://localhost:4200`; no mezclar localhost/127.0.0.1.
No hay proxy: CORS y cookie HttpOnly se ejercitan directamente.
Producción requiere HTTPS/Secure y hosting con fallback Router a `index.html`.

## Calidad

```bash
npm run web:contracts
npm run web:test
npm run web:lint
npm run web:build
npm exec --prefix apps/web -- playwright install chromium
npm run web:smoke
```

Build: `dist/catalog-assistant/browser`. Tests unitarios Vitest/HttpTestingController,
fixtures sólo en tests. Smoke Playwright con API/OpenAI reales y bases temporales
(catálogo 3001, Application API 3101); necesita frontend4200 levantado y la credencial autorizada sólo en
backend. Consume API paga; no se ejecuta dentro de `web:test` ni CI automáticamente.

`/chat` ya permite escribir directamente: la conversación se crea recién al primer envío.
«Nueva conversación» vuelve a ese estado sin crear un registro vacío. «Filtros» o `/`
abre el menú de filtros guardados reales. No hay subida de adjuntos, micrófono, Admin UI,
streaming ni mutaciones de catálogo en esta etapa.

Detalles: `../../docs/web/angular-foundation.md`, `../../docs/web/checkpoint-6c.md`,
`../../docs/web/auto-conversation.md`, `../../docs/web/saved-filter-command-menu.md`
y `../../docs/web/design-language.md`.
