# Política de ambigüedad y aclaraciones

## Principio

Preguntar solamente cuando la ambigüedad pueda cambiar materialmente la operación, sus argumentos o el objeto al que se aplica. La pregunta debe solicitar el dato mínimo suficiente.

## Actuar sin preguntar

- Una búsqueda parcial pero válida: “Buscame bife ancho”.
- Una comparación de 2–10 códigos explícitos.
- Una referencia ordinal resoluble contra la lista visible más reciente.
- Una operación de lectura inequívoca.
- Un refinamiento que agrega, reemplaza o elimina claramente un criterio.

No se piden mercado, temperatura, envase o peso solo porque podrían acotar una búsqueda. Tras responder, pueden ofrecerse como refinamientos opcionales.

## Preguntar

- Un pronombre no tiene antecedente claro: “uno como ese” sin referencia.
- Existen varios conjuntos recientes y “comparalos” no identifica cuál.
- Un ordinal excede la lista o la lista relevante no puede determinarse.
- Un término no puede mapearse con seguridad a metadata: “súper fría” no equivale por defecto a `REFRIGERADO` o `CONGELADO`.
- Falta información obligatoria: guardar sin búsqueda actual, comparar menos de dos artículos, similarity sin referencia ni features.
- Varios filtros guardados podrían corresponder al mismo nombre o expresión.
- La corrección del usuario no permite identificar qué criterio debe cambiar.

## Referencias conversacionales

Se admiten `este`, `ese`, `estos`, `esos`, `el primero`, `el segundo`, `el tercero`, `el anterior`, `los anteriores`, `los dos` y `los tres` cuando hay un antecedente inequívoco.

Prioridad conceptual:

1. selección explícita más reciente;
2. entidades mencionadas en el turno inmediatamente anterior;
3. resultados visibles de la operación relevante más reciente;
4. referencia singular más reciente compatible con la acción.

La resolución conserva el orden mostrado al usuario. Nunca se elige arbitrariamente entre candidatos igualmente plausibles.

## Valores y metadata

Antes de estructurar un campo, operador o enum dudoso, el agente usa la metadata disponible. Puede normalizar expresiones inequívocas (`bife ancho` → `BIFE_ANCHO`, `mercado chino` → `CHINA`), pero no crea aliases regulatorios o comerciales sin definición.

Si la API rechaza un campo o valor, el agente no corrige silenciosamente hacia otro. Explica la limitación y, si existe una alternativa inequívoca en metadata, la ofrece.

## Required ambiguo

La presencia de un atributo en una solicitud de similarity no basta para hacerlo required. Solo se eleva a required con lenguaje de obligatoriedad claro. Si la frase admite dos interpretaciones materialmente distintas, se pregunta si es preferencia o requisito.

## Correcciones

“No, cuando dije China me refería a Brasil” reemplaza `CHINA` por `BRASIL`, elimina el valor anterior y vuelve a ejecutar la operación correspondiente. No se conserva como una lista `[CHINA, BRASIL]`.

## Operaciones personales

La identidad de usuario no se obtiene del lenguaje del usuario y no puede ser modificada por el modelo. Si la aplicación no proporciona una identidad válida, se informa que la operación sobre filtros personales no puede completarse; no se inventa una identidad.
