# Persistencia de ADK — Etapa 6A

Se usan tres bases separadas, ignoradas por Git y privadas:

| Base | Propósito |
|---|---|
| `apps/agent/var/application.db` | Identidad, conversaciones, mensajes, runs, tools, UI y audit |
| `apps/agent/var/intake.db` | Adjuntos y ArticleRequestDraft |
| `apps/agent/var/adk_sessions.db` | Session/State y eventos conversacionales oficiales de ADK |

Sus rutas son configurables. Catalog API conserva su propia DB/schema.

Conversation ID y ADK Session ID se generan separadamente y se relacionan mediante
Conversation.adk_session_id. La Application API utiliza DatabaseSessionService
de ADK 2.10.0 con `sqlite+aiosqlite`, nunca consulta tablas internas del runtime.
El wrapper sobrescribe únicamente append_event público para excluir razonamiento
privado. ADK administra su schema oficial; Alembic versiona sólo Application DB.

Cerrar/recrear los servicios recupera la misma Session. El test de persistencia
envía “Buscame bife ancho”, cierra la API y pools, vuelve a abrir las bases, envía
“Solo los de China” y comprueba BIFE_ANCHO + CHINA usando un modelo determinístico
y el runtime real. Otra conversación del mismo usuario obtiene state nuevo.

No se configura MemoryService ni memoria automática entre conversaciones.
ADK Web sigue como playground de desarrollo con su almacenamiento independiente;
la aplicación no depende de `.adk/session.db` y el futuro Angular consumirá
Application API.

Application DB es la fuente de verdad del historial para la UI. Abrir conversación
o historial sólo lee persistencia. Si el agente falla después de eventos parciales,
el run queda FAILED y la sesión puede contener esos eventos: no se realiza replay
automático ni una falsa respuesta. La reconciliación de ejecuciones interrumpidas
es una limitación explícita de la demo.
