# De medio día de trabajo manual a una decisión que llega sola

**El antes.** Cada día, la integración entre el AS/400 y SAP generaba el log `HA00`: 2.474 errores en un archivo plano, pipe-separado, con migración y stock mezclados. No es que nadie lo mirara — había un analista dedicado a eso. El problema era el costo: abrir el CSV, clasificar a mano, cruzar por cliente, armar el resumen y decidir a quién avisar le tomaba **medio día**, todos los días. Trabajo valioso convertido en tarea mecánica.

**El quiebre.** La pregunta no fue "¿cómo lee mejor el analista el CSV?", sino "¿por qué un analista está haciendo a mano lo que una regla puede hacer sola?". Así nació el pipeline: serverless, nativo en AWS, sin servidores que mantener.

**El viaje de un lote.** El archivo aterriza en S3 y eso enciende todo. Una Lambda **analizadora** aplica siete reglas de causa raíz y agrupa por cliente — el código calcula las cifras, auditable. CloudWatch **detecta** por severidad y abre el abanico del lote. Luego entra la pieza que cambia el tono: una Lambda **sintetizadora** con Bedrock que redacta la narrativa. La IA escribe, pero el código manda: si Bedrock falla, hay plantilla de respaldo y la alerta nunca se bloquea por la IA.

**No es "un correo", son dos entregables.** De la síntesis salen dos caminos complementarios:

- **El tablero en vivo.** Los errores quedan catalogados en Glue y consultables con Athena; Power BI se conecta en vivo sobre la tabla `errores_detalle`. Cuatro páginas: resumen ejecutivo, causa raíz tipo Pareto, responsables y detalle filtrable — incluso en el celular. Es la capa de **análisis y tendencia**: dónde está el 80% del dolor y a quién le toca.
- **El correo accionable.** Un único mail HTML por lote, con las cifras ya cruzadas, el runbook y el responsable por causa raíz. No es un aviso, es un **llamado a la acción**: quién hace qué, ahora.

El mismo dato en dos velocidades: la urgencia que llega a la bandeja de entrada y la tendencia que se consulta en el tablero.

**El después.** El medio día de trabajo manual se vuelve un proceso automático que entrega **el tablero y el correo** sin intervención. 2.474 líneas se consolidan para ~370 clientes reales, y el análisis revela que una sola causa — clientes sin interlocutores en SAP — explica 1.480 casos. El analista deja de clasificar y pasa a **decidir y actuar** sobre información ya digerida.

**El cierre.** No le quitamos el trabajo al analista: le quitamos la parte mecánica. Convertimos medio día de clasificar a mano en dos entregables que llegan solos — uno para entender, otro para actuar.
