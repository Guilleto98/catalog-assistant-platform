# Flujo de similitud

`find_similar_articles` delega siempre en `POST /api/v1/articles/similar` y
admite un solo modo: referencia, características explícitas o borrador actual.
El agente no calcula puntajes, coincidencias ni aptitud. Conserva sin
reinterpretar `MATCH`, `MISMATCH`, `NOT_AVAILABLE`, `ELIGIBLE` e `INELIGIBLE`.

Los candidatos aptos y no aptos permanecen separados aun si un no apto tiene
mayor puntaje. `last_similarity` guarda sólo modo, referencia/borrador y códigos
ordenados de ambos grupos. Así, “el primero apto” y “el primero no apto” son
referencias inequívocas sin almacenar respuestas grandes.

No se ejecuta similitud automáticamente al confirmar un borrador. Si no hay
aptos se explica el resultado y no se promocionan no aptos ni se crea un artículo.
La creación y clonación siguen deshabilitadas hasta la Etapa 5C.

