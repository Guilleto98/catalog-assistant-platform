# Asistente de catálogo — proyecto final

> **Guía rápida para evaluación y ejecución local.** El sistema es una demo académica: usa un catálogo ficticio con datos sintéticos y no está desplegado como servicio público ni preparado todavía para producción.

## Descripción general

El proyecto implementa un asistente conversacional que consulta un catálogo estructurado. El modelo interpreta las preguntas y decide cuándo usar herramientas; las búsquedas, los detalles, las comparaciones y los datos de artículos se obtienen de una API determinística. El agente no debe inventar datos del catálogo.

```text
Usuario → Angular → Application API (FastAPI + identidad + auditoría)
                             ↓
                   Agente Google ADK → herramientas → Catalog API (NestJS)
                             ↓                         ↓
                        OpenAI API                 SQLite demo
```

Google ADK es el framework de orquestación del agente. El modelo de lenguaje y los servicios de transcripción/extracción configurados usan OpenAI a través del backend. La clave nunca se configura en Angular ni se publica en el repositorio.

## Tecnologías y organización

| Aplicación | Tecnologías principales | Responsabilidad |
| --- | --- | --- |
| `apps/web/` | Angular 22, TypeScript, SCSS | Login, chat, conversaciones y filtros guardados. |
| `apps/agent/` | Python 3.12, FastAPI, Google ADK, LiteLLM, SQLAlchemy/Alembic | Agente, Application API autenticada, identidad, conversaciones, auditoría e intake documental. |
| `apps/catalog-api/` | Node.js 22, NestJS, TypeScript, Prisma, SQLite | API de catálogo, búsqueda, detalle, comparación, similitud y filtros. |
| `docs/` | Markdown y OpenAPI | Arquitectura, contratos, diseño, evaluaciones y guías operativas. |

`packages/contracts/` conserva tipos conceptuales históricos; no es la fuente runtime de los contratos HTTP. La fuente vigente de la API del agente es `docs/contracts/`; Angular genera sus tipos desde OpenAPI.

## Funcionalidades de la demo

- Login con sesión por cookie, roles de usuario y conversaciones persistidas.
- Consulta conversacional del catálogo: búsqueda, detalle, comparación y búsqueda de artículos similares.
- Filtros guardados y continuidad de contexto dentro de una conversación.
- Registro auditable de ejecuciones y herramientas del agente.
- Backend para analizar PDF/XLSX y transcribir audio; la interfaz Angular todavía no ofrece carga de esos adjuntos.
- Datos de demostración sintéticos: no representan artículos ni información real de una empresa.

No incluye creación o clonación de artículos, interfaz administrativa, SSO/MFA ni despliegue productivo. El detalle de capacidades pendientes está en [la arquitectura general](docs/architecture/system-overview.md) y en las guías de cada aplicación.

## Requisitos

- Node.js **22.22.3 o superior dentro de la serie 22**, npm incluido. Esta versión satisface los requisitos del catálogo y Angular 22. También se admite una versión de Node compatible con Angular 22; véase la [tabla oficial de compatibilidad](https://angular.dev/reference/versions).
- Python 3.12 y [`uv`](https://docs.astral.sh/uv/).
- Una clave de API de OpenAI para ejecutar respuestas reales del agente. Las llamadas a la API pueden tener costo según el uso; las pruebas unitarias no necesitan llamar al modelo.
- Docker es opcional si se prefiere ejecutar la Catalog API en contenedor.

## Instalación inicial

Desde la raíz del repositorio, instalar las dependencias una sola vez:

```bash
npm run api:install
npm run api:db:generate
npm run api:db:reset
npm run agent:install
npm run web:install
```

`api:db:reset` inicializa el catálogo de demostración y vuelve a cargar su dataset; al hacerlo también reinicia los filtros guardados del catálogo local. No lo uses para conservar cambios locales.

Crear el archivo de configuración del agente y agregar la clave de OpenAI en `OPENAI_API_KEY`:

```bash
cp apps/agent/.env.example apps/agent/.env
```

`apps/agent/.env` está excluido de Git. **No pegues la clave en el README, en `apps/web/public/config.json`, en capturas ni en un commit.** El frontend no necesita una clave.

## Levantar el sistema

Abrir tres terminales en la raíz del proyecto y mantenerlas abiertas:

1. Catalog API:

   ```bash
   npm run api:dev
   ```

2. Application API y agente:

   ```bash
   npm run agent:api
   ```

3. Frontend Angular:

   ```bash
   npm run web:dev
   ```

No hace falta ejecutar `npm run agent:dev` para usar la interfaz: ese comando abre el playground de desarrollo de ADK, separado de la aplicación web.

Direcciones locales:

- Aplicación: <http://localhost:4200>
- Catalog API: <http://localhost:3000/api/v1>
- Documentación Swagger del catálogo: <http://localhost:3000/api/docs>
- Application API del agente: <http://localhost:3100>
- Documentación OpenAPI del agente: <http://localhost:3100/docs>

Usa `localhost` en todas las direcciones del navegador. El origen del frontend debe coincidir exactamente con `FRONTEND_ORIGIN` en `apps/agent/.env` (por defecto `http://localhost:4200`); no mezcles `localhost` y `127.0.0.1` para el frontend.

### Crear una cuenta de prueba local

Con las dependencias instaladas, ejecutar una sola vez desde la raíz:

```bash
npm run agent:demo:login
```

El comando crea el usuario local `demo.local@solvo.test` con rol `CLIENT_USER` y una contraseña aleatoria. La guarda en `apps/agent/var/local-login.txt`, archivo privado e ignorado por Git. Usa esos datos en <http://localhost:4200/login>. La cuenta sólo existe en la base local donde se creó; otra persona que clone el proyecto debe generar su propia cuenta. **No publiques ni incluyas la contraseña en este README o en GitHub.** Para compartir acceso a una instancia que ya está corriendo, envía la credencial por un canal privado.

Si el comando indica que la cuenta ya existe, no cambia su contraseña. La guía de [identidad y bootstrap](docs/platform/identity.md) explica cómo crear otros usuarios y organizaciones.

## Comprobación y casos de evaluación

Con los servicios levantados, verificar primero que se puede iniciar sesión y abrir una conversación. Después probar, por ejemplo:

1. “Buscá bife ancho congelado para China.”
2. “¿Cuál es el envase del artículo 900001?”
3. “Compará los artículos 900001 y 900002.”
4. “Buscá artículos similares al 900001 para Brasil.”
5. Guardá un filtro y comprobá que siga disponible al recargar la aplicación.
6. Hacé una pregunta ajena al catálogo y verificá que el agente la redirija o pida aclaración, sin inventar información.

Las respuestas sobre artículos deben poder contrastarse con la Catalog API. La guía [Escenarios de evaluación](docs/evals/conversational-scenarios-v1.md) contiene más casos; [Auditoría](docs/platform/audit.md) explica qué queda registrado.

Pruebas automatizadas principales:

```bash
npm run api:test
npm run api:test:e2e
npm run agent:test
npm run web:test
npm run web:lint
npm run web:build
```

`npm run agent:test:integration` requiere la Catalog API disponible. `npm run agent:smoke`, `npm run agent:scope:smoke` y `npm run web:smoke` realizan llamadas reales y pueden consumir crédito de la API de OpenAI.

## Mapa de documentación

- [Índice general](docs/README.md): documentación vigente y fuentes canónicas.
- [Visión general y principios](docs/architecture/system-overview.md) y [organización del monorepo](docs/architecture/monorepo.md).
- [Catalog API](apps/catalog-api/README.md): ejecución, endpoints, dataset, arquitectura y pruebas.
- [Agente y Application API](apps/agent/README.md): herramientas, configuración, intake, pruebas y límites conocidos.
- [Contrato HTTP del agente](docs/contracts/application-api-v1.md) y [OpenAPI](docs/contracts/application-api-v1.openapi.json).
- [Identidad y creación de cuentas](docs/platform/identity.md), [conversaciones](docs/platform/conversations.md), [auditoría](docs/platform/audit.md) y [sesiones ADK](docs/platform/adk-session-persistence.md).
- [Angular: arquitectura y comandos](docs/web/angular-foundation.md), [experiencia de usuario](docs/web/design-language.md) y [entrega 6D](docs/web/checkpoint-6d.md).
- [Definición del agente](docs/agent/agent-definition.md), [flujos conversacionales](docs/agent/conversational-flows.md), [contratos de herramientas](docs/agent/tool-contracts.md) y [evaluaciones](docs/evals/conversational-scenarios-v1.md).
