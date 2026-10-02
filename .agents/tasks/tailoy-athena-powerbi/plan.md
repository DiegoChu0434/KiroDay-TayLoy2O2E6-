# Implementation Plan — Rama analítica (Athena → Power BI) en el diagrama de flujo Tai Loy

Archivo ÚNICO a modificar:
`/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/docs/diagrams/flujo-alertas-dataflow-full.html`

NO tocar ningún otro archivo. NO modificar el `<img class="brand-logo" src="data:image/png;base64,...">` (línea ~72). NO hacer commits. NO introducir colores nuevos.

---

## Contexto y decisiones de diseño (cerradas)

Este es un HTML estático con un SVG inline (`viewBox="0 0 728 456"`, líneas ~76–209). No hay build ni test runner; la verificación es visual abriendo el archivo en el navegador. La paleta y las coordenadas de abajo salen de leer el SVG real.

Geometría actual relevante (confirmada en el archivo):
- `<svg viewBox="0 0 728 456">` (línea 76). CSS `svg { width:100%; min-width:728px; display:block; }` (línea 59). No hay `min-height`.
- Fondos: `<rect width="728" height="456" fill="#f6faf7"/>` (88) y `<rect ... fill="url(#dots-full)" .../>` (89).
- Banda de encabezado: `<rect x="0" y="0" width="728" height="36" .../>` (90).
- Banda lateral de zonas: `<rect x="0" y="36" width="140" height="320" .../>` (91) → termina en y=356.
- Sombreado de carriles alternos: `<rect x="0" y="116" width="728" height="80" .../>` (94) y `<rect x="0" y="276" width="728" height="80" .../>` (95).
- Líneas de carril horizontales en y=36,116,196,276,356 (97–101). Divisor vertical `x=140` de y=36 a y=356 (102).
- Carriles de 80px: ORIGEN 36–116, ANÁLISIS 116–196, OBSERVA. 196–276, NOTIFICA. 276–356.
- Etiquetas laterales (x=70, mono, `fill="#006B39"`, 2 líneas en centro de carril ±6): ORIGEN/AS·S3 (120–121), ANÁLISIS/LAMBDA (122–123), OBSERVA./CW·SNS (124–125), NOTIFICA./LAMBDA·SES (126–127).
- Nodos (100×64): Sintetizadora `rect x=482 y=284` texto centrado x=532 (167–176); Correo accionable `rect x=594 y=284` texto centrado x=644 (178–185). Ambos hoy en y=284 dentro del carril NOTIFICA.
- Flecha Sintetizadora→Correo actual: `<path d="M 582 316 L 594 316" ... stroke="#006B39" stroke-dasharray="2,2" marker-end="url(#arr-link-f)"/>` (134).
- Pill de datos existente: `rect x=534 y=250 w=66 h=12 fill="#FFDA00"` + texto "RESUMEN JSON" (132–133).
- Marcadores en `<defs>` (83–85): `arr-muted-f` (#008C4B), `arr-accent-f` (#008C4B), `arr-link-f` (#006B39).
- Leyenda inferior (dentro del SVG, debajo de y=356): STEPS y=376 (187–192), DATOS y=390/397 (194–199), FOCO y=412/419 (201–203), FLUJO y=437/440 (205–208).
- `</svg>` en 209; `.cards` (grid) empieza en 212; `.footer` en 242.

**Decisión de layout (Opción A, cerrada por el usuario):**
- Añadir UN carril nuevo de 80px para separar la fila de ENTREGA de la Sintetizadora. La Sintetizadora se queda en el carril actual (y=276..356). Debajo se abren dos carriles nuevos:
  - Carril ANALÍTICA-ATHENA: y=356..436 (banda sombreada). Aquí vive **Athena** (columna derecha, misma columna que Correo/Power BI, texto x=644).
  - Carril ANALÍTICA-ENTREGA: y=436..516. Aquí viven **Correo accionable** (columna izquierda, texto x=532) y **Power BI** (columna derecha, texto x=644), AMBOS a la MISMA y.
- Es decir: Correo baja desde y=284 (carril Sintetizadora) hasta y=444 (carril de entrega). Mantiene su COLUMNA no exactamente: el usuario pidió "Correo y PowerBI al mismo nivel" como prioridad #1; para que ambos quepan lado a lado en la fila de entrega, Correo ocupa la columna de la Sintetizadora (x=482, texto x=532) y Power BI la columna de Athena/Correo-original (x=594, texto x=644). Esto cumple: (a) Correo baja un nivel respecto a Sintetizadora; (b) Correo y Power BI comparten y; (c) Athena queda un nivel por encima de Power BI, colgando de la Sintetizadora.

Mapa de carriles resultante (altura total nueva):
```
y=0..36    encabezado (steps 01..05)
y=36..116  ORIGEN      — S3 (sin cambios)
y=116..196 ANÁLISIS    — Analizadora (sin cambios)
y=196..276 OBSERVA.    — Métricas+SNS (sin cambios)
y=276..356 NOTIFICA.   — Sintetizadora (sin cambios de posición)
y=356..436 ANALÍTICA · ATHENA (NUEVO) — Athena (col. der., x rect 594, texto 644)
y=436..516 ANALÍTICA · ENTREGA (NUEVO) — Correo (col. izq., x rect 482, texto 532) + Power BI (col. der., x rect 594, texto 644)
```

**Nuevo tamaño del SVG:** se añaden 2 carriles de 80px = +160px. Nueva altura total = 456 + 160 = **616**. La leyenda inferior (STEPS/DATOS/FOCO/FLUJO, hoy en y=376..440) se desplaza +160 para quedar debajo del nuevo carril de entrega (nuevos y: 536, 550/557, 572/579, 597/600). La banda lateral y el divisor vertical se extienden de y=356 a y=516.

**Paleta (sólo estos; NO introducir azul #1e4389 ni ámbar #b8915a ni ningún otro):**
`#008C4B` (verde marca), `#006B39` (verde profundo), `#FFDA00` (amarillo), ink `#0b2e1c`/`#10241a`, textos `#2f6b4a` y `#4d8064`, fondos `#f6faf7` y `rgba(0,140,75,α)` / `rgba(255,218,0,α)`, blanco `#fff` para texto sobre relleno oscuro.

**Trazo diferenciado para la rama analítica:** la rama operativa usa el verde sólido/punteado existente. Para distinguir la rama analítica sin colores nuevos, se añade un marcador y un estilo de línea en verde profundo `#006B39` con `stroke-dasharray="5,3"` (guion más largo que el `2,2` del "entregado"), reutilizando el color de marca. Se añade una entrada a la leyenda FLUJO para este nuevo estilo ("analítica / ODBC").

---

## Ítems del plan (ordenados por dependencia; cada uno deja el archivo abrible en navegador)

- [ ] 1. Agrandar el lienzo del SVG y los fondos para dar espacio a los 2 carriles nuevos.
      Cambios: `viewBox="0 0 728 456"` → `viewBox="0 0 728 616"` (línea 76). Los dos `<rect width="728" height="456" ...>` de fondo (88 fill `#f6faf7`, 89 fill `url(#dots-full)`) → `height="616"`. Añadir en el CSS (línea 59) `min-height` NO es necesario porque el SVG escala por `viewBox`; en su lugar confirmar que `svg { width:100%; min-width:728px }` se mantiene (el alto se deriva del viewBox). Opcional recomendado para evitar que el SVG quede demasiado alto en pantallas anchas: no tocar el CSS (el ratio del viewBox se encarga).
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: abrir el archivo en el navegador; el SVG se dibuja sin recortes y el fondo de puntos cubre toda la nueva altura (hasta y=616). El patrón de puntos no debe cortarse.

- [ ] 2. Extender la banda lateral de zonas y el divisor vertical a los nuevos carriles.
      Cambios: `<rect x="0" y="36" width="140" height="320" .../>` (91) → `height="480"` (36..516). Divisor vertical `<line x1="140" y1="36" x2="140" y2="356" .../>` (102) → `y2="516"`.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador, la banda lateral verde claro y la línea divisoria x=140 llegan hasta abajo del nuevo carril de entrega (y=516), sin huecos.

- [ ] 3. Añadir el sombreado alterno y las líneas de carril de los 2 carriles nuevos.
      Cambios: tras el `<rect ... y="276" ...>` (95) añadir un `<rect x="0" y="436" width="728" height="80" fill="rgba(0,140,75,0.05)"/>` (sombreado del carril de entrega; el carril Athena 356..436 queda claro, alternando como hoy). Añadir dos `<line>` horizontales con el mismo estilo (`stroke="rgba(0,140,75,0.25)" stroke-width="0.8"`): una en `y=436` y otra en `y=516` (la de y=356 ya existe en la línea 101). Insertar junto al bloque de líneas 97–101.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador se ven 2 carriles nuevos delimitados por líneas en y=356, 436 y 516, con el carril de entrega sombreado y el de Athena claro, consistente con el patrón alterno de arriba.

- [ ] 4. Añadir las etiquetas laterales de zona para los 2 carriles nuevos (estilo mono, `fill="#006B39"`).
      Cambios: replicar el patrón de las etiquetas 120–127 (x=70, `font-family="var(--font-mono)" font-size="8" font-weight="500" letter-spacing="0.18em" fill="#006B39"`, 2 líneas en centro de carril ±6). Carril Athena (centro y=396): línea 1 `ANALÍTICA` en y=392, línea 2 `ATHENA` en y=404. Carril entrega (centro y=476): línea 1 `ENTREGA` en y=472, línea 2 `BI · CORREO` en y=484.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador aparecen las etiquetas `ANALÍTICA`/`ATHENA` y `ENTREGA`/`BI · CORREO` centradas en x=70, mismo tamaño/color/espaciado que ORIGEN/ANÁLISIS/OBSERVA./NOTIFICA.

- [ ] 5. Mover el nodo 'Correo accionable' al carril de entrega (baja un nivel; columna izquierda).
      Cambios: en el bloque 178–185 reubicar el nodo. Rect contenedor `x=594 y=284` → `x=482 y=444` (misma anchura 100×64; carril entrega top y=436, nodo centrado verticalmente en y=444..508). El sub-rect del badge SES `x=598 y=288` → `x=486 y=448`. Textos: título x=644→x=532 y=310→y=470; subtítulos x=644→x=532, y=322→y=482 y y=334→y=494; badge "SES" x=608→x=496, y=295.5→y=455.5; badge inferior "FL" rect x=598 y=338 → x=486 y=498 y su texto x=606 y=344 → x=494 y=504. (Desplazamiento: Δx=−112, Δy=+160 respecto a la posición original.) Mantener todos los colores actuales del nodo (borde `#008C4B`, badge `#FFDA00`, texto título `#006B39`, etc.).
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador 'Correo accionable' aparece en el carril de entrega (y≈444), columna izquierda (centrado en x=532), un nivel por debajo de la Sintetizadora, con sus badges y textos intactos.

- [ ] 6. Añadir el nuevo nodo 'Athena' en el carril ANALÍTICA·ATHENA (columna derecha, un nivel por encima de Power BI).
      Cambios: insertar un bloque de nodo 100×64 siguiendo el patrón de la Sintetizadora/Correo. Rect contenedor `x=594 y=364 rx=6 fill="#f6faf7" stroke="#008C4B" stroke-width="1"` (carril Athena top y=356, nodo centrado en y=364..428). Badge superior izq. `rect x=598 y=368 w=20 h=10 rx=3 fill="#FFDA00"` + texto `x=608 y=375.5 ... fill="#0b2e1c"` con etiqueta `ATH`. Textos centrados en x=644: título `y=390 font-size=9 font-weight=600 fill="#0b2e1c"` = `Athena`; subtítulo `y=402 font-size=6.5 fill="#2f6b4a"` = `tabla errores_detalle`; subtítulo `y=414 font-size=6.5 fill="#4d8064"` = `consulta en vivo`. Badge de datos inferior `rect x=662 y=418 w=16 h=8 rx=3 fill="#FFDA00"` + texto `x=670 y=424 ... fill="#0b2e1c"` = `TB` (coherente con la leyenda DATOS "TB tabla"). Textos de alto nivel, sin DSN ni credenciales.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador 'Athena' aparece en la columna derecha (centrado x=644) en el carril intermedio, entre la Sintetizadora (arriba) y la fila de entrega (abajo), con estilo de tarjeta consistente.

- [ ] 7. Añadir el nuevo nodo 'Power BI' en el carril de entrega (columna derecha, MISMA y que Correo).
      Cambios: insertar nodo 100×64. Rect contenedor `x=594 y=444 rx=6 fill="#f6faf7" stroke="#008C4B" stroke-width="1"` (misma y que Correo del ítem 5 → MISMA fila). Badge superior izq. `rect x=598 y=448 w=20 h=10 rx=3 fill="#FFDA00"` + texto `x=608 y=455.5 ... fill="#0b2e1c"` = `BI`. Textos centrados en x=644: título `y=470 font-size=9 font-weight=600 fill="#006B39"` = `Power BI`; subtítulo `y=482 font-size=6.5 fill="#2f6b4a"` = `4 páginas · Pareto`; subtítulo `y=494 font-size=6.5 fill="#4d8064"` = `tablero + vista móvil`. Badge inferior opcional `rect x=662 y=498 w=16 h=8 rx=3 fill="#008C4B"` + texto `x=670 y=504 fill="#fff"` = `LS` (lectura/consulta). Textos de alto nivel (nada de pasos de configuración).
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador 'Power BI' aparece en la columna derecha a la MISMA altura que 'Correo accionable' (ambos centrados verticalmente en y≈476), confirmando el requisito prioritario del usuario.

- [ ] 8. Redibujar la flecha operativa Sintetizadora→Correo (ahora baja un carril) y añadir las dos flechas de la rama analítica.
      Cambios:
      (a) Reemplazar la flecha corta actual `M 582 316 L 594 316` (134) por un trazo que baje de la Sintetizadora (borde inferior en x≈532, y=348) al nuevo Correo (borde superior en x=532, y=444): `<path d="M 532 348 L 532 444" fill="none" stroke="#006B39" stroke-width="1" stroke-dasharray="2,2" marker-end="url(#arr-link-f)"/>` (mantiene el estilo "entregado" existente). Ajustar los puntos exactos a los bordes reales del nodo movido en el ítem 5.
      (b) Flecha analítica Sintetizadora→Athena, con trazo diferenciado: desde el borde derecho/inferior de la Sintetizadora hacia Athena. Ruta sugerida `<path d="M 582 316 L 630 316 Q 644 316 644 330 L 644 364" fill="none" stroke="#006B39" stroke-width="1.2" stroke-dasharray="5,3" marker-end="url(#arr-analytic-f)"/>` (marcador nuevo del ítem 9). Añadir pill tipo "CONSULTA": `rect x=600 y=338 w=52 h=12 rx=2 fill="#FFDA00"` + texto `x=626 y=347 font-family="var(--font-mono)" font-size=8 letter-spacing=0.06em font-weight=700 fill="#0b2e1c"` = `CONSULTA`. Ajustar coordenadas a los bordes reales de ambos nodos.
      (c) Flecha Athena→Power BI con label `ODBC`: `<path d="M 644 428 L 644 444" fill="none" stroke="#006B39" stroke-width="1.2" stroke-dasharray="5,3" marker-end="url(#arr-analytic-f)"/>` y pill `rect x=620 y=430 w=48 h=12 rx=2 fill="#FFDA00"` + texto `x=644 y=439 ... font-weight=700 fill="#0b2e1c"` = `ODBC`.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador se ve que la Sintetizadora bifurca en dos ramas: una punteada corta hacia Correo (abajo) y otra con guion largo hacia Athena, y de Athena baja a Power BI con el label ODBC. Ninguna flecha se cruza de forma confusa ni queda tapada por un nodo.

- [ ] 9. Añadir el marcador de flecha `arr-analytic-f` para la rama analítica (sin color nuevo).
      Cambios: en `<defs>` (83–85) añadir `<marker id="arr-analytic-f" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#006B39"/></marker>` (mismo verde profundo que `arr-link-f`; se distingue por el `stroke-dasharray="5,3"` de las líneas, no por color). Debe existir antes de usarse en el ítem 8.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: las flechas analíticas del ítem 8 muestran su punta de flecha correctamente (no quedan líneas sin marcador) al abrir el archivo.

- [ ] 10. Desplazar la leyenda inferior (STEPS/DATOS/FOCO/FLUJO) +160px para que quede debajo del nuevo carril de entrega.
      Cambios: en el bloque 187–208 sumar 160 a cada coordenada `y`: STEPS y textos 376→536; DATOS 390/397→550/557 (rects y textos); FOCO 412/419→572/579; FLUJO 437/440→597/600. Mantener las x. (Alternativa: envolver el bloque en `<g transform="translate(0,160)">...</g>`; elegir la que menos riesgo de error introduzca — se recomienda el `<g transform>` para no editar ~22 coordenadas a mano.)
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador la leyenda (STEPS/DATOS/FOCO/FLUJO) aparece completa debajo del carril de entrega, sin solaparse con los nodos Correo/Power BI ni salirse del viewBox (y máx ~600 < 616).

- [ ] 11. Añadir a la leyenda FLUJO la entrada del nuevo estilo de línea analítica.
      Cambios: en la fila FLUJO (ahora en y≈597/600 tras el ítem 10) añadir un cuarto item tras "entregado": una `<line ... stroke="#006B39" stroke-width="1.2" stroke-dasharray="5,3" marker-end="url(#arr-analytic-f)"/>` seguida de un `<text ... fill="#006B39">analítica · ODBC</text>`. Colocarla a la derecha del item "entregado" respetando el espaciado horizontal del resto de la fila (p. ej. línea en x≈500→520, texto en x≈526); ajustar x para que no se salga de x=728.
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: en el navegador la leyenda FLUJO muestra 4 estilos: hand-off, entrada a IA, entregado y el nuevo "analítica · ODBC" con el guion largo, sin desbordar el ancho del SVG.

- [ ] 12. Verificación integral de layout: solapamientos, tarjetas y footer.
      Cambios: ninguno nuevo; revisión. Confirmar que: (a) ningún nodo nuevo pisa las líneas de carril ni la banda lateral x=0..140; (b) los pills (CONSULTA, ODBC) no quedan tapados por nodos; (c) la leyenda cabe en y<616; (d) tras `</svg>` (209) el bloque `.cards` (212) y el `.footer` (242) HTML siguen debajo del SVG sin solaparse (al crecer el viewBox el SVG ocupa más alto, pero `.cards`/`.footer` son hermanos en el flujo del documento, así que simplemente bajan; confirmar visualmente que no hay recorte ni superposición).
      Files: `docs/diagrams/flujo-alertas-dataflow-full.html`
      Verify: abrir el archivo en el navegador a ancho completo y a ~800px; comprobar visualmente los 4 puntos anteriores. El diagrama debe leerse como: síntesis → (abajo) Correo + (rama analítica) Athena → Power BI, con Correo y Power BI a la misma altura.

---

## Notas y supuestos

- Las coordenadas de las flechas (ítem 8) se dan como punto de partida; al colocar los nodos reales conviene ajustarlas a los bordes exactos de cada rect para que arranquen/terminen pegadas al nodo. No cambian la estructura ni la paleta.
- Se eligió `<g transform="translate(0,160)">` como opción recomendada para desplazar la leyenda (ítem 10) por ser menos propenso a errores que editar ~22 valores `y`.
- Supuesto de columnas en la fila de entrega: Correo en la columna de la Sintetizadora (x texto 532) y Power BI en la columna de Athena (x texto 644). Esto prioriza el requisito explícito #1 ("Correo y PowerBI al mismo nivel") y mantiene a Athena colgando como eslabón intermedio sobre Power BI. Si se prefiriera que Correo conserve su columna original (x=644), Power BI tendría que ir a la izquierda; se descartó porque rompería la lectura "Athena encima de Power BI" en la misma columna.
- No se dibujan Glue ni S3 en esta vista (ya están en el diagrama de arquitectura); la rama analítica representa sólo Athena (tabla errores_detalle) → Power BI, con trazo diferenciado para no sugerir flujo operativo síncrono.
- No se tocó el base64 del logo, ni se añadieron colores fuera de la paleta aprobada.
