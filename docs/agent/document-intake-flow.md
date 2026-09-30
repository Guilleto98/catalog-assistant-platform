# Flujo de ingreso documental

```text
Audio ── upload ── transcribe ── texto normal de conversación

PDF/XLSX ── upload ── parser determinístico ── contenido con ubicación
         ── extracción estructurada ── validación contra metadata del catálogo
         ── ArticleRequestDraft ── revisión humana ── READY
```

El parser no interpreta instrucciones: extrae texto o celdas. El contenido llega
al modelo delimitado como dato no confiable y sin herramientas del catálogo. La
salida satisface un schema Pydantic y luego se controla de forma determinística:

1. el `field` existe en los metadatos reales;
2. tipo y enum son válidos;
3. página o celda existieron en el contenido parseado;
4. los datos dudosos quedan `NEEDS_CLARIFICATION`;
5. nada escribe en Catalog API.

Un PDF sin texto devuelve `PDF_REQUIRES_OCR`; OCR queda fuera de 5A. Las
planillas se abren en modo lectura, sin ejecutar macros, con límite de celdas.
Si no existe ningún criterio válido, se devuelve
`NO_EXTRACTABLE_REQUEST_FIELDS` y no se fabrica un borrador vacío. La respuesta
de análisis incluye `state_update` para que el futuro frontend copie únicamente
los IDs seguros a la sesión ADK.

Los logs registran request, duración, estado, tipo e IDs, pero no el contenido
completo. Para producción todavía corresponden autenticación, object storage,
cifrado, retención, antivirus, colas y métricas centralizadas.
