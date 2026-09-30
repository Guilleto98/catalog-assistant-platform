# Creación diferida de conversaciones

`/chat` no crea registros. «Nueva conversación» del sidebar navega a `/chat` y limpia el contexto visual; pulsarla repetidamente no llena la base con conversaciones vacías.

Al enviar el primer texto, el frontend bloquea envíos duplicados, hace `POST /conversations` una vez, guarda el texto original para ese ID, navega a `/chat/{id}` y, tras cargar la conversación, envía el mensaje mediante el mecanismo 6C. Ese envío genera un único `clientMessageId` y, ante un fallo de red, se reconsulta/reintenta con ese mismo ID. Si falla la creación, el composer conserva el texto y permite reintentar. Si la navegación falla después de crear, el siguiente intento reutiliza el ID creado, evitando otro registro vacío.

El estado en memoria de primer mensaje y envíos pendientes se borra al terminar la sesión. El backend sigue siendo la fuente de verdad del historial y de los UiEvents. La recarga reconstruye el chat sin llamar nuevamente al modelo.
