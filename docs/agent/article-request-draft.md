# ArticleRequestDraft

Un documento no crea ni modifica artículos. Produce una propuesta revisable:

```text
ArticleRequestDraft
  id, conversation_id, source_attachment_ids
  status: DRAFT | NEEDS_REVIEW | READY
  fields[]
    field, raw_value, normalized_value
    status: PROPOSED | CONFIRMED | CORRECTED | REJECTED | NEEDS_CLARIFICATION
    required
    source: PDF(page) | SPREADSHEET(sheet, cell) | USER
    history[]
```

`raw_value` conserva el documento; `normalized_value` es la propuesta compatible
con los metadatos de Catalog API. `required` distingue requisito de preferencia.
`source` vuelve a la página o celda exacta y `history` preserva la procedencia
anterior ante una corrección humana.

El borrador queda `NEEDS_REVIEW` mientras haya propuestas o ambigüedades. Es
`READY` sólo cuando todos los campos fueron confirmados, corregidos o rechazados.
Esto tampoco crea un artículo.

`GET /drafts/{id}` recupera el borrador y `POST /drafts/{id}/review` permite
`confirm`, `correct` o `reject`. Las correcciones se revalidan contra
`/metadata/filterable-fields`; un enum inexistente no se guarda silenciosamente.
