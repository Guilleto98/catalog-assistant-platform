# Semantic Domain Scope Guardrail

## Propósito

El asistente es útil dentro del dominio de artículos de catálogo, fichas
técnicas, especificaciones, pedidos comerciales y documentos relacionados. No
actúa como asistente generalista. El control no selecciona herramientas ni
decide si una capacidad está implementada: sólo evalúa el ámbito semántico.

## Decisiones

- `IN_SCOPE`: tarea propia del dominio, follow-up contextual, consulta de
  capacidades o capacidad todavía no habilitada.
- `ADJACENT_ALLOWED`: conocimiento general materialmente útil para interpretar
  una ficha o requisito.
- `OUT_OF_SCOPE`: tarea generalista independiente. El Root Agent se omite y se
  devuelve una redirección breve.
- `AMBIGUOUS`: falta contexto. El Root Agent se omite y se pide una aclaración
  orientada al dominio.

## Integración ADK

`DomainScopeCallback` implementa la firma oficial de
`before_model_callback` de Google ADK 2.10.0. El clasificador corre antes del
Root Agent. La decisión, razón, latencia y si se omitió el agente quedan en
Session State como `domain_scope_*` y en logs estructurados con el ID de
conversación. En llamadas posteriores al modelo dentro de la misma invocación no
se repite la clasificación.

El input contiene solamente:

- mensaje que inició la invocación, truncado;
- hasta cuatro fragmentos textuales recientes, truncados;
- booleanos, conteos y referencias pequeñas del estado.

Nunca incluye el PDF/XLSX crudo ni outputs grandes de tools.

## Clasificador

Usa OpenAI Structured Outputs con `DomainScopeResult` validado por Pydantic:

```text
decision: IN_SCOPE | ADJACENT_ALLOWED | OUT_OF_SCOPE | AMBIGUOUS
reason: explicación breve de auditoría
request_kind: NORMAL | MIXED | INTERNAL_CONFIGURATION
```

Se configura con `DOMAIN_SCOPE_ENABLED`, `DOMAIN_SCOPE_MODEL` y
`DOMAIN_SCOPE_TIMEOUT_SECONDS`. El modelo predeterminado es `gpt-4.1-mini`, del
mismo provider OpenAI, elegido para reducir costo y latencia frente al modelo
principal.

## Casos especiales

- Solicitudes mixtas inequívocas continúan al Root Agent con una instrucción
  acotada: atiende la parte válida y redirige la externa.
- Consultas sobre capacidades funcionales están dentro del dominio.
- Solicitudes de prompts, credenciales o configuración reciben una respuesta
  estática y no llegan al Root Agent.
- Instrucciones dentro de documentos, catálogo o tool results son datos no
  confiables y no cambian el scope.
- Una función no disponible, como similitud o creación, sigue siendo in-scope.

## Fallos y limitaciones

El fallo técnico del clasificador se registra como `FAIL_OPEN` y permite la
conversación porque la versión actual sólo consulta y revisa borradores. Este
control no reemplaza autorización, confirmación ni revalidación para futuras
mutaciones. **MUST REVISIT BEFORE MUTATIONS:** cambiar o complementar esta
estrategia antes de altas, clonaciones o mutaciones masivas.

La clasificación agrega una llamada de modelo por turno. El baseline local de
5A.1 fue mínimo 1,55 s, máximo 2,41 s y promedio 2,12 s. Su latencia se guarda en
`domain_scope_latency_ms`, separada del middleware HTTP de intake, del timing del
cliente de Catalog API y del tiempo total del Root Agent. Optimizarla es deuda de
UX, no bloqueo para 5B.
