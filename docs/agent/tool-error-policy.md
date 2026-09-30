# Política de errores de tools

## Envelope

Una tool nunca entrega excepciones arbitrarias al modelo:

```ts
type ToolResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ToolError }

interface ToolError {
  code: string
  message: string
  category:
    | 'VALIDATION' | 'NOT_FOUND' | 'UNAUTHORIZED'
    | 'FORBIDDEN' | 'UPSTREAM' | 'TIMEOUT' | 'UNKNOWN'
  retryable: boolean
  details?: Record<string, unknown>
}
```

`message` debe ser accionable para el agente sin revelar implementación. `details` se limita a campos seguros que permitan corregir argumentos; nunca incluye stack, SQL, credenciales, headers, URL interna ni cuerpos inesperados completos.

## Mapeo de errores reales de la API

| API code | HTTP observado | Category | Retryable | Exposición al modelo |
| --- | ---: | --- | --- | --- |
| `VALIDATION_ERROR` | 400 | `VALIDATION` | No | Código y resumen seguro; omitir payload interno de class-validator salvo fields seguros |
| `INVALID_FILTER_FIELD` | 400 | `VALIDATION` | No | Exponer field rechazado; sugerir metadata |
| `INVALID_FILTER_OPERATOR` | 400 | `VALIDATION` | No | Exponer operador/field seguros |
| `INVALID_FILTER_VALUE` | 400 | `VALIDATION` | No | Exponer razón de tipo/enum de forma segura |
| `INVALID_PAGINATION` | 400 | `VALIDATION` | No | Exponer rango permitido: page >= 1, pageSize 1..50 |
| `INVALID_COMPARISON` | 400 | `VALIDATION` | No | Exponer 2–10 códigos únicos |
| `INVALID_SIMILARITY_REQUEST` | 400 | `VALIDATION` | No | Exponer exclusión reference/features y limit 1..10 |
| `INVALID_REQUIRED_CRITERION` | 400 | `VALIDATION` | No | Exponer field/valor rechazado sin reinterpretarlo |
| `ARTICLE_NOT_FOUND` | 404 | `NOT_FOUND` | No | Indicar que el artículo no existe/no está disponible |
| `TECHNICAL_SHEET_NOT_FOUND` | 404 | `NOT_FOUND` | No | Indicar ficha no encontrada |
| `SAVED_FILTER_NOT_FOUND` | 404 | `NOT_FOUND` | No | Indicar filtro inexistente o no accesible; no revelar ownership de terceros |
| `DEMO_USER_REQUIRED` | 400 | `UNAUTHORIZED` | No | Abstraer como contexto de usuario ausente; el modelo no puede corregir userId |
| `DEMO_USER_NOT_FOUND` | 404 | `UNAUTHORIZED` | No | Abstraer como identidad de aplicación inválida |
| `INTERNAL_ERROR` | 500 | `UPSTREAM` | Sí, con cautela | Mensaje genérico; ocultar detalles |

La API demo no emite actualmente un código `FORBIDDEN`; la categoría queda disponible para evolución de permisos. Ownership deliberadamente devuelve `SAVED_FILTER_NOT_FOUND` para recursos ajenos.

## Transporte

| Condición | Tool code | Category | Retryable | Mensaje seguro |
| --- | --- | --- | --- | --- |
| Conexión rechazada/DNS/API inaccesible | `CATALOG_API_UNAVAILABLE` | `UPSTREAM` | Sí | El catálogo no está disponible temporalmente. |
| Timeout configurado | `CATALOG_API_TIMEOUT` | `TIMEOUT` | Sí | La consulta excedió el tiempo disponible. |
| Respuesta no parseable o contrato inesperado | `CATALOG_API_INVALID_RESPONSE` | `UPSTREAM` | Sí | La respuesta del catálogo no pudo procesarse. |
| Error no clasificado | `TOOL_UNKNOWN_ERROR` | `UNKNOWN` | No por defecto | No se pudo completar la operación. |

El timeout será configurable. No se fija un número en esta etapa.

## Qué llega al usuario

El modelo puede convertir el error normalizado en lenguaje de tarea:

- validation: pedir/corregir solo el argumento necesario;
- not found: informar que la entidad no fue encontrada;
- unauthorized: informar que el contexto de usuario no permite completar la operación;
- upstream/timeout retryable: informar indisponibilidad y ofrecer reintento;
- unknown: reconocer que no pudo completar la operación.

Nunca debe presentar datos anteriores como si fueran la respuesta actual ni inventar un fallback.

## Logging futuro

La capa backend podrá registrar `conversationId`, tool, argumentos saneados, duración, status y error code. Los detalles técnicos completos permanecen fuera del resultado visible al modelo y deben respetar minimización de datos. No se implementa observabilidad en la Etapa 3.
