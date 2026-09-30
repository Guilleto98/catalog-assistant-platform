# Adjuntos — Etapa 5A

El Agent Backend acepta audio, PDF con texto y XLSX. Los binarios se guardan en
filesystem local detrás de `AttachmentStorage`; SQLite conserva metadatos. La
Session State de ADK nunca contiene bytes ni rutas: sólo
`current_attachment_ids` y `current_request_draft_id`.

- Audio: `.webm`, `.mp3`, `.mp4`, `.m4a`, `.wav`.
- Documentos: `.pdf` y `.xlsx`.
- Tamaño predeterminado: 25 MiB, configurable.

Cada request incluye `X-Demo-Conversation-Id`. El backend valida que el recurso
pertenezca a esa conversación. Esta cabecera aísla la demo, pero no sustituye la
autenticación real de producción.

## API

- `POST /attachments`: multipart con campo `file`.
- `GET /attachments/{id}`: estado y metadatos, nunca la ruta interna.
- `POST /attachments/{id}/transcribe`: sólo audio.
- `POST /attachments/{id}/analyze`: sólo PDF/XLSX.

Estados: `UPLOADED → PROCESSING → READY | ERROR`. Los fallos tienen códigos
estables. Una carga parcial se elimina. El nombre físico es un UUID generado por
el backend, por lo que el nombre recibido no puede controlar la ruta.

El backend valida conjuntamente extensión, MIME y firma mínima del contenido.
El directorio local usa permisos `0700` y cada adjunto `0600`. Un fallo durante
la carga elimina el archivo parcial. Un PDF/XLSX ya cargado que falle al
procesarse se conserva deliberadamente como adjunto administrado en estado
`ERROR`; no es un temporal huérfano y puede auditarse o eliminarse mediante una
política de retención futura.

La configuración completa está en `apps/agent/.env.example`.
