# Mutaciones futuras

V1 no crea ni edita artículos. Una futura alta, edición individual o masiva debe separar intención y aplicación:

1. `preview`: valida el cambio y muestra exactamente qué registros/campos afectaría.
2. El servidor genera un token de operación corto, opaco, con vencimiento y ligado al usuario y payload.
3. `confirm` recibe ese token; nunca un simple `confirmed: true` en el request original.
4. El servidor revalida versión y registros afectados para detectar cambios concurrentes.
5. Solo entonces aplica la operación en una transacción y registra auditoría.

Autenticación, autorización, idempotencia y rollback deberán diseñarse antes de habilitar mutaciones reales.
