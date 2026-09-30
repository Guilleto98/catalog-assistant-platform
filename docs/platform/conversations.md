# Conversaciones y mensajes — Etapa 6A

`npm run agent:api` es el comando canónico de la Application API en el puerto
3100. `agent:intake` sigue siendo alias compatible. Swagger está en `/docs`.

Endpoints de producto:

- `POST /conversations`: crea una conversación con sesión ADK nueva.
- `GET /conversations`: página de conversaciones propias.
- `GET /conversations/{id}`: metadatos, sin ejecutar el agente.
- `GET /conversations/{id}/messages`: historial, referencias a adjuntos y UiEvents.
- `POST /conversations/{id}/messages`: ejecuta un turno.
- `POST /conversations/{id}/archive`: archivo lógico, sin borrado físico.

Los listados reciben `page` y `pageSize` (máximo 100), y devuelven `items`, `page`,
`pageSize`, `total`. Los DTOs provisionales usan nombres de columnas snake_case;
el request de mensaje usa `clientMessageId`, `text`, `attachmentIds`. La etapa 6B
congelará el contrato definitivo.

Ejemplo de envío después de login y creación de conversación:

```json
{
  "clientMessageId": "ee402fe6-72f2-4b69-915c-eb71fca01065",
  "text": "Buscame bife ancho para China.",
  "attachmentIds": []
}
```

Se guarda el mensaje USER y AgentRun STARTED antes de llamar al agente. Después
se guarda ASSISTANT y se completa la ejecución. El título inicial se actualiza
con los primeros 80 caracteres del primer mensaje, sin una llamada extra al LLM.
En fallo se conserva USER y se marca FAILED con error seguro.

La restricción única `(conversation_id, client_message_id)` proporciona
idempotencia. Repetir idéntico mensaje devuelve la ejecución existente, incluyendo
STARTED o FAILED; no vuelve a ejecutar tools. Reutilizar la clave para otro texto
o adjuntos devuelve 409. Una carrera concurrente puede responder 409 y requiere
consultar/reintentar la misma clave. Un índice parcial permite una sola ejecución
STARTED por conversación, también entre procesos.

Una interrupción abrupta durante una ejecución puede dejar STARTED durable.
No se repite automáticamente porque las herramientas pueden haber actuado.
La demo requiere intervención administrativa explícita para reconciliar ese run;
no se implementa recuperación automática de trabajos en esta etapa.

Los binarios y borradores siguen en Intake DB/storage. MessageAttachmentReference
guarda sólo IDs; antes del envío se verifica la propiedad de la conversación.
Upload, análisis y revisión autenticados generan auditoría. El análisis actualiza
el state de ADK mediante append_event oficial para asociar el borrador actual.

Cada conversación está aislada por propietario y organización. Conocer un ID no
confiere acceso. Leer historial no invoca ADK ni OpenAI. No hay eliminación ni
retención automática; se definirán políticas antes de producción.
