# Paleta Tai Loy dominante en los diagramas de flujo y arquitectura

Se re-tematizaron `flujo-alertas-dataflow-full.html` y `arquitectura-aws-full.html` para que el verde `#008C4B` y el amarillo `#FFDA00` sean los colores dominantes. Antes eran solo acentos sobre grises, azul `#1e4389` y ámbar `#b8915a`. Los dos archivos comparten un bloque `:root` con los mismos tokens. La cabecera pasa a ser una banda verde profundo con bordes de marca. Las flechas, bordes y zonas van en verde, y los pills, etiquetas de flecha y chips de servicio en amarillo, siempre como relleno con texto oscuro. Los estados que antes se distinguían por color (azul = entrega, ámbar = pendiente) ahora se distinguen por el tipo de trazo dentro de la misma familia verde.

Watch for: la cabecera rediseñada empuja todo el contenido ~80 px hacia abajo; es un cambio de layout de página, no de SVG (confirmed). El anillo `#FFDA00` alrededor del logo deja ver que el amarillo del logo es algo más apagado que el de marca (confirmed, visual). Ninguno de los dos es bloqueante.

**Verdict**: APPROVED

## High-level view

En cuanto a dominancia, las capturas "después" ya no se leen como gris claro con algún toque verde. La banda verde de la cabecera, los carriles teñidos, los bordes y flechas en verde, y los bloques amarillos (pills, RESUMEN JSON, Analizadora, CloudWatch Alarm, Power BI, SES, chips de etiqueta) ocupan buena parte de la superficie de ambos diagramas. Las capturas "antes" mostraban azul en SES y "entregado", y ámbar/marrón en TB, FL y "pendiente". Nada de eso aparece después.

Los dos diagramas usan los mismos roles de color. Verde `#008C4B` para la estructura, verde profundo `#006B39` para texto pequeño y chips con texto claro, amarillo para rellenos de énfasis y tinte amarillo para nodos de clasificación o salida. El foco de IA es la Sintetizadora en ambos: relleno verde translúcido, borde grueso y chip AI amarillo sobre verde. Las tarjetas inferiores repiten el patrón en los dos: borde superior verde, viñetas verdes y punto amarillo con anillo verde para "resultado/estado".

En legibilidad, el amarillo nunca lleva texto encima sobre fondo claro. Siempre es relleno con texto ink, o texto amarillo sobre `#006B39` (≈4.8:1). El único caso por debajo de 4.5:1 es el chip "LS" (blanco sobre `#008C4B`, ≈4.3:1). Es un rótulo de 2 letras que también aparece en la leyenda.

Dentro del SVG, el layout no cambió: los nodos, las flechas y los textos están en las mismas posiciones relativas que en las capturas "antes". Las únicas alteraciones geométricas son de fondo: dos rects de franja en flujo y el backplate de "RESUMEN JSON", que se ensanchó porque el texto ya lo desbordaba. Fuera del SVG, la cabecera sí ganó padding y fondo, lo que desplaza la página hacia abajo.

En el alcance, `git status` muestra cuatro archivos modificados. Los dos HTML son del coder. `infra/cloudformation.yaml` (mtime 14:30:57) ya estaba modificado antes de que se creara la carpeta de la tarea (14:31). `docs/infraestructura-desplegada.md` (14:39:22) agrega una sección "5.2 Desincronización stack ↔ Lambda viva" que no tiene relación con los colores. `apply_palette.py` solo escribe en `docs/diagrams/<name>` para los dos `*-full.html`, así que esos dos archivos no son obra del coder.

<details>
<summary>Issues (3)</summary>

1. **Cabecera desplaza el layout de página** — La banda verde con padding baja el contenido ~80 px en ambos HTML (confirmed). Es aceptable como parte de "que los colores dominen"; si se exige que el layout de página sea idéntico, quitar el padding extra y dejar solo el color de fondo.
2. **Anillo amarillo vs. amarillo del logo** — El anillo de 3 px en `#FFDA00` queda pegado al relleno amarillo del PNG embebido, que es más apagado, y la diferencia se nota (confirmed, visual). Opcional: un anillo blanco o verde evita la comparación directa. No se debe tocar el logo.
3. **Chip "LS" en ≈4.3:1** — El texto blanco de 5 px sobre `#008C4B` queda justo bajo AA (confirmed por las notas del coder). Opcional: pasar el chip a `#006B39`, aunque así se parecería más a "DB". Se puede mantener tal cual porque la leyenda lo explica.

</details>

<details>
<summary>Details</summary>

### Dominancia de marca en las capturas

En `flujo-despues.png`, la cabecera es una banda `#006B39` de ancho completo con eyebrow amarillo y un borde inferior amarillo grueso, y es el bloque de color más grande de la página. La franja de pasos y la banda de carriles a la izquierda llevan tinte verde. Los pills 01/02/03/05 son amarillos sólidos y el 04 (focal) es verde profundo con número amarillo. La Analizadora tiene tinte amarillo con borde verde, "RESUMEN JSON" es una etiqueta amarilla sólida y todas las flechas son verdes. La leyenda (DB verde profundo, TB amarillo, LS verde, FL casi negro) ya no tiene marrón ni azul. Las tres tarjetas inferiores llevan borde superior verde.

En `arquitectura-despues.png` el patrón es el mismo. Se suman las etiquetas amarillas de flecha (OBJECT, JSON, INVOKE, SEND, MÉTRICAS, PENDIENTE, ODBC), el chip amarillo de la cuenta AWS, los chips verde profundo de zona con texto amarillo y los tintes amarillos de CloudWatch Alarm, Correo HTML (SES) y Power BI. Antes, Correo HTML era azul grisáceo y Power BI ámbar pálido. Ahora los dos están en la familia amarilla de marca.

Comparadas lado a lado con las capturas "antes", que eran casi monocromas en gris y crema, la diferencia de saturación cumple con "que esos colores dominen".

### Colores fuera de marca

Un grep acotado de `#1e4389|#b8915a|rgba(94,122,155|rgba(30,67,137` da 0 en los dos archivos. Según el coder, el grep ampliado (azules, ámbar, marrones y neutros viejos, `color-link`) también da 0, y fuera de la línea del logo solo quedan tokens de la paleta. Lo que se ve en las capturas coincide: no hay tonos azules ni ámbar.

### Estados por trazo en lugar de por color

Antes, "entregado / envío externo" se marcaba en azul y "pendiente" en ámbar. Ahora entrega/consulta externa usa `#006B39` con trazo `2,2`, pendiente usa `#4d8064` con `5,4` y métricas usa verde con `4,3`. En las capturas los tres se distinguen: SEND y ODBC se ven punteados finos y PENDIENTE de trazo largo, y las leyendas reflejan la nueva convención. El estado pendiente pierde algo de contraste respecto al resto, pero la etiqueta amarilla "PENDIENTE" lo compensa.

### Cabecera y logo

La cabecera era texto sobre fondo claro y ahora es una banda verde, con h1 y subtítulo en blanco (≈6.6:1). El cambio de padding y fondo empuja el SVG unos 80 px hacia abajo en ambas páginas. No afecta a las coordenadas internas del SVG, pero es un cambio de layout de página que va más allá de "solo colores". Es coherente con el objetivo, así que no lo bloqueo.

El logo base64 no cambió (el SHA-256 coincide). El anillo amarillo de 3 px que lo rodea es `#FFDA00` puro, mientras que el relleno del logo se ve algo más oscuro y oliváceo, y en la captura se nota el escalón entre ambos.

</details>

<details>
<summary>File map</summary>

- `docs/diagrams/flujo-alertas-dataflow-full.html`: tokens `:root` de marca, cabecera en banda verde, re-coloreado del SVG (pills, carriles, chips, flechas, leyenda), 2 rects de fondo añadidos y backplate de "RESUMEN JSON" ensanchado.
- `docs/diagrams/arquitectura-aws-full.html`: los mismos tokens y CSS; re-coloreado del SVG (zonas, chips de zona, etiquetas de flecha, nodos SES/BI/Alarm, leyenda); swatch focal de la leyenda alineado.
- Fuera del alcance y no tocados por el coder: `infra/cloudformation.yaml` (ya estaba modificado antes) y `docs/infraestructura-desplegada.md` (sección 5.2, la editó otro proceso).

Diff completo: `git -C /Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy diff -- docs/diagrams/flujo-alertas-dataflow-full.html docs/diagrams/arquitectura-aws-full.html`

</details>
