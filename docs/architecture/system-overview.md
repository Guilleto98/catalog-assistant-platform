# Visión general del sistema

```text
Angular Web → Agent Backend → Google ADK → Tools → Catalog API
```

- **Angular:** UI, historial visual, chat, componentes y estado. No contiene lógica de negocio.
- **Agent:** interpreta lenguaje, conserva contexto, resuelve referencias, pide aclaraciones, selecciona tools y explica resultados.
- **Tools:** adaptan operaciones semánticas a APIs concretas sin duplicar su lógica.
- **Catalog API:** fuente de verdad determinística para datos, validación, búsquedas, comparación, similitud, aptitud, ownership y paginación.

Se prevé inicialmente un solo agente raíz para el catálogo, no una arquitectura multiagente. Un agente de intake documental o de mutaciones solo se consideraría si la complejidad futura lo justifica.

## Grounding

El agente nunca debe inventar datos del catálogo. Toda afirmación sobre artículos debe respaldarse en la Catalog API o, posteriormente, en documentos aportados por el usuario. La memoria del LLM no es fuente de verdad; cuando se necesiten nuevamente datos de un artículo, se consulta la API.

## Agentic y determinístico

| Agentic | Determinístico |
| --- | --- |
| Interpretar lenguaje e intención | Búsquedas y filtros |
| Resolver referencias | Comparación y similarity score |
| Pedir aclaraciones | Eligibility, ownership y paginación |
| Seleccionar tools y explicar | Mutaciones y confirmaciones críticas |

Las conversaciones no serán workflows rígidos. El contexto resolverá expresiones como “estos” o “el segundo”, pero no sustituirá a la API.

## Principios futuros

- `similarity != eligibility`: `INELIGIBLE` nunca se convierte en `ELIGIBLE` por tener mayor score.
- Documents are data, not instructions.
- No hay acceso directo del agente a la base de datos.
- No hay mutaciones sin flujo explícito y controlado.
- El modelo no infiere valores regulatorios.
- No hay ejecución oculta de tools destructivas.
