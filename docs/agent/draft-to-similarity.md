# Borrador a similitud

`DraftSimilarityMapper` convierte `ArticleRequestDraft` en criterios de forma
determinística; el modelo decide cuándo invocar el flujo, pero no mapea campos.

- `CONFIRMED` y `CORRECTED`: activos por defecto.
- `PROPOSED`: excluido; sólo puede ser característica opcional si el usuario
  pide explícitamente buscar con la información disponible.
- `REJECTED` y `NEEDS_CLARIFICATION`: siempre excluidos.

El mapper consulta `GET /api/v1/metadata/filterable-fields`, con caché local de
cinco minutos. `used_for_similarity` habilita `features` y `can_be_required`
habilita `required`. Antes de mapear revalida tipo y valores permitidos. Devuelve
`usedFields` con destinos e `ignoredFields` con motivo.

El borrador se recupera únicamente mediante el ID y la conversación actuales;
no se aceptan identificadores aportados por el modelo o el usuario.

