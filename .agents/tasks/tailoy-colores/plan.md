# Plan: paleta Tai Loy dominante en 2 diagramas

Archivos (SOLO estos dos, mismo tratamiento en ambos):
- A = docs/diagrams/flujo-alertas-dataflow-full.html (logo base64 en línea 64)
- B = docs/diagrams/arquitectura-aws-full.html (logo base64 en línea 63)

Rutas absolutas bajo /Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/. No leer las líneas del logo (usar offset/limit o awk que trunque líneas >2000 chars). No tocar -dark, base, .png, .svg. Sin commits.

## Decisiones

- Verde #008C4B = color estructural: flechas de flujo, bordes de nodos/zonas, bordes superiores de tarjetas, franja de cabecera. Neutros derivados del matiz del verde (ink #0b2e1c, muted #2f6b4a, soft #4d8064).
- Amarillo #FFDA00 = segundo color, siempre como relleno: badges de pasos, fondos de etiquetas de flecha, chips, nodo "clasificación", Power BI/alarma, eyebrow, borde inferior del masthead.
- Verde profundo #006B39 (derivado) se usa para texto pequeño verde y como fondo de cualquier chip que lleve texto blanco o amarillo. Contraste: blanco/#006B39 ≈ 6.6:1, #FFDA00/#006B39 ≈ 4.8:1. Blanco/#008C4B da solo ≈ 4.3:1, así que #008C4B nunca va de fondo para texto pequeño.
- El masthead usa #006B39 como banda, con borde superior de 8px en #008C4B y borde inferior de 6px en #FFDA00. Así el subtítulo blanco pasa AA, y los dos colores oficiales quedan como franjas visibles.
- Los estados se distinguen sin colores ajenos:
  - flujo = verde #008C4B sólido
  - focal = verde más grueso + etiqueta amarilla
  - entrega/externo = #006B39 punteado `2,2`
  - pendiente = soft #4d8064 discontinuo `5,4`
  - métricas = verde discontinuo `4,3` (como hoy)
- Se eliminan del todo #1e4389, rgba(30,67,137,*), #b8915a, rgba(184,145,90,*), rgba(255,212,0,*), #5e7a9b, rgba(94,122,155,*), #4a7c59 y #9c6b50.

## Roles de color

| Rol | Color |
|---|---|
| paper (fondo) | #f6faf7 |
| paper-2 | #e6f3ec |
| ink (texto principal) | #0b2e1c |
| muted (texto secundario) | #2f6b4a |
| soft (texto terciario, pendiente) | #4d8064 |
| rule (líneas) | rgba(0,140,75,0.25) |
| accent (estructura/flujo) | #008C4B |
| accent-deep (texto verde pequeño, entrega, chips) | #006B39 |
| accent-tint (rellenos) | rgba(0,140,75,0.10) |
| yellow (resalte) | #FFDA00 |
| yellow-tint | rgba(255,218,0,0.28) |

## Implementation Plan

- [ ] 1. Redefinir CSS en A y B (idéntico en ambos).
      En `:root`, reemplazar el bloque de colores por el siguiente y borrar `--color-link`:
      ```
      /* Tai Loy · Digital: Verde R0 G140 B75 #008C4B · Amarillo R255 G218 B0 #FFDA00
         Impresión: Verde C100 M10 Y100 K10 · Amarillo C0 M12 Y100 K0 */
      --color-paper:#f6faf7; --color-paper-2:#e6f3ec; --color-ink:#0b2e1c; --color-muted:#2f6b4a;
      --color-soft:#4d8064; --color-rule:rgba(0,140,75,0.25); --color-accent:#008C4B;
      --color-accent-deep:#006B39; --color-accent-tint:rgba(0,140,75,0.10);
      --color-yellow:#FFDA00; --color-yellow-tint:rgba(255,218,0,0.28); --color-on-accent:#ffffff;
      ```
      Cambios en las reglas:
      - `.masthead`: añadir `background:var(--color-accent-deep); border-top:8px solid var(--color-accent); border-bottom:6px solid var(--color-yellow); border-radius:10px; padding:1.75rem 2rem; align-items:center`. En A, la clase va en `.header.masthead`; mantener su margin-bottom.
      - `.header-eyebrow`: `display:inline-block; background:var(--color-yellow); color:var(--color-ink); padding:0.3rem 0.55rem; border-radius:3px; font-weight:600`.
      - `h1`: color `var(--color-on-accent)`. `.subtitle`: color `#ffffff`.
      - `.brand-bar`: el primer span pasa a `var(--color-yellow)` y el segundo a `#ffffff`.
      - `.brand-logo`: añadir `box-shadow:0 0 0 3px var(--color-yellow)`.
      - `.card`: añadir `border-top:4px solid var(--color-accent)`. `.card-header`: border-bottom `rgba(0,140,75,0.25)`. `.card h3`: color `var(--color-accent-deep)`. `.card li::before`: color `var(--color-accent)`.
      - `.card-dot.link` (A) y `.card-dot.amber` (B): `background:var(--color-yellow); box-shadow:0 0 0 1.5px var(--color-accent-deep)`. `.card-dot.ink`: `var(--color-ink)`.
      - `.footer`: `border-top:2px solid var(--color-accent); color:var(--color-muted)`.
      Files: A, B (solo el bloque `<style>`).
      Verify: abrir ambos en navegador (paso 4). El masthead se ve como una banda verde con borde amarillo y no hay errores de CSS.

- [ ] 2. Recolorear el SVG de A (flujo). Solo cambian atributos fill/stroke/stroke-width/stroke-dasharray/font-weight; se añaden 2 rects de fondo.
      Defs y fondo:
      - Patrón de puntos: `rgba(16,36,26,0.10)` → `rgba(0,140,75,0.16)`.
      - Marcadores: `arr-muted-f` → `#008C4B`, `arr-accent-f` se queda en `#008C4B`, `arr-link-f` → `#006B39`.
      - `#fafaf7` → `#f6faf7` en todas sus apariciones.
      - Justo después del rect `url(#dots-full)`, insertar `<rect x="0" y="0" width="728" height="36" fill="rgba(0,140,75,0.10)"/>` y `<rect x="0" y="36" width="140" height="320" fill="rgba(0,140,75,0.08)"/>`.
      - Bandas `rgba(16,36,26,0.018)` → `rgba(0,140,75,0.05)`. Líneas `rgba(16,36,26,0.12)` → `rgba(0,140,75,0.25)`.
      Pasos y carriles:
      - Pills 01, 02, 03 y 05: fill `#FFDA00`, número `#0b2e1c`.
      - Pill 04: fill `#006B39`, número `#FFDA00`.
      - Etiquetas INGESTA, CLASIFICA, DETECTA y ENTREGA: `#006B39`. SINTETIZA: `#006B39` con font-weight 700.
      - Etiquetas de carril (ORIGEN…LAMBDA · SES): `#4a7a5f` → `#006B39`.
      Flechas:
      - hand-off: `#4a7a5f` → `#008C4B`.
      - RESUMEN JSON: stroke-width 1.4 → 2. Backplate `#FFDA00`; texto `#0b2e1c` con font-weight 700.
      - Entrega `M 582 316`: `#1e4389` → `#006B39` con `stroke-dasharray="2,2"`.
      Nodos:
      - Nodos neutros (CSV y CW):
        - stroke `rgba(16,36,26,0.25)` → `rgba(0,140,75,0.55)`
        - chips de icono `rgba(16,36,26,0.12)` → `rgba(0,140,75,0.14)`
        - `#10241a` → `#0b2e1c`, `#4a7a5f` → `#2f6b4a`, `#7fae92` → `#4d8064` (en todo el SVG)
      - Analizadora (clasificación):
        - fill → `rgba(255,218,0,0.22)`, stroke → `#008C4B`
        - chip → `#FFDA00`; texto λ y "Analizadora" → `#0b2e1c`
      - Sintetizadora (focal):
        - fill → `rgba(0,140,75,0.14)`, stroke-width → 1.8
        - chip AI → `#006B39` con texto `#FFDA00`
      - SES:
        - stroke `rgba(30,67,137,0.4)` → `#008C4B`
        - chip → `#FFDA00`; texto SES → `#0b2e1c`
        - "Correo accionable" → `#006B39`
      Chips de datos (nodos y leyenda DATOS):
      - DB `#5e7a9b` → `#006B39`, texto `#fff`
      - TB `#b8915a` → `#FFDA00`, texto `#0b2e1c`
      - LS `#4a7c59` → `#008C4B`, texto `#fff`
      - FL `#9c6b50` → `#0b2e1c`, texto `#FFDA00`
      Leyenda:
      - Títulos STEPS, DATOS, FOCO y FLUJO: `#006B39` con font-weight 700.
      - "04 sintetiza": `#006B39`.
      - FOCO "clasificación": rect `rgba(94,122,155,0.5)` → `#FFDA00` con `stroke="#008C4B" stroke-width="0.6"`.
      - "síntesis con IA" texto → `#006B39`.
      - FLUJO: "entrada a IA" pasa a stroke-width 2 y texto `#006B39` bold. "entregado" pasa a `#006B39` con dasharray `2,2` y texto `#006B39`.
      Files: A.
      Verify: `grep -Eic '1e4389|30,67,137|b8915a|184,145,90|5e7a9b|94,122,155|4a7c59|9c6b50|255,212,0|16,36,26|#10241a|#4a7a5f|#7fae92|#fafaf7'` sobre A devuelve 0 (solo como apoyo). Además, ejecutar el paso 4.

- [ ] 3. Recolorear el SVG de B (arquitectura) con los mismos roles.
      Defs y fondo:
      - Puntos: igual que en A.
      - Marcadores: `arrow-f` → `#008C4B`, `arrow-link-f` → `#006B39`, `arrow-pend-f` → `#4d8064`.
      - `#fafaf7` → `#f6faf7`.
      Límite de cuenta y zonas:
      - Límite de cuenta: stroke → `rgba(0,140,75,0.6)`.
      - Backplate "AWS · …": fill → `#FFDA00`; texto → `#0b2e1c` con font-weight 700.
      - Zonas 1 y 2: fill → `rgba(0,140,75,0.05)`, stroke → `rgba(0,140,75,0.40)`.
      - Backplates de etiqueta de zona: fill → `#006B39`. Texto `rgba(16,36,26,0.45)` → `#FFDA00` con font-weight 700.
      Flechas:
      - Flujo S3→Analyzer, Analyzer→SNS y las 2 primeras de la fila de analítica: `#4a7a5f` → `#008C4B`.
      - Métricas: `#008C4B`, se mantiene dasharray `4,3`.
      - INVOKE: stroke-width 1.6 → 2.2.
      - Verticales Email↔Bedrock: sin cambios.
      - SEND y ODBC: `#1e4389` → `#006B39` con `stroke-dasharray="2,2"`.
      - PENDIENTE: `#b8915a` → `#4d8064`, se mantiene `5,4`.
      - Todas las backplates de etiqueta (OBJECT, JSON, INVOKE, SEND, MÉTRICAS, PENDIENTE, ODBC): fill `#FFDA00`; texto `#0b2e1c` con font-weight 700.
      Nodos:
      - Nodos neutros (S3 ingesta, Analyzer, SNS, curated, Glue, Athena):
        - stroke `rgba(16,36,26,0.30)` → `rgba(0,140,75,0.55)`, fill `rgba(16,36,26,0.03)` → `rgba(0,140,75,0.05)`
        - chip: fill `transparent` → `rgba(0,140,75,0.12)`, stroke → `rgba(0,140,75,0.5)`; texto `#4a7a5f` → `#006B39`
      - Sintetizadora (focal):
        - fill → `rgba(0,140,75,0.14)`, stroke-width → 1.8
        - chip AI: fill → `#006B39`, stroke → `#006B39`; texto → `#FFDA00`
      - SES:
        - fill → `rgba(255,218,0,0.18)`, stroke → `#008C4B`
        - chip: stroke → `#008C4B`; texto → `#006B39`
      - Bedrock: fill → `rgba(0,140,75,0.10)`, stroke → `#008C4B`.
      - CloudWatch Alarm: fill → `rgba(255,218,0,0.28)`, stroke → `#008C4B`.
      - Power BI:
        - fill → `rgba(255,218,0,0.30)`, stroke → `#008C4B`
        - chip: fill → `#FFDA00`, stroke → `#008C4B`; texto BI → `#0b2e1c`
      Texto: `#10241a` → `#0b2e1c`, `#4a7a5f` → `#2f6b4a`, `#7fae92` → `#4d8064`.
      Leyenda:
      - LEYENDA: `#006B39` bold.
      - "Envío / consulta externa": `#006B39`, dasharray `2,2`.
      - Pendiente: `#4d8064`, `5,4`.
      - Rect de cuenta: stroke → `rgba(0,140,75,0.6)`.
      - Textos: `#2f6b4a`.
      Files: B.
      Verify: el mismo grep de apoyo del paso 2 devuelve 0 sobre B. Ejecutar el paso 4.

- [ ] 4. Verificación visual y de integridad, sobre ambos archivos.
      Integridad:
      - `python3 -c "import html.parser,sys;[html.parser.HTMLParser().feed(open(f).read()) for f in sys.argv[1:]]" A B`: parsea sin excepción.
      - `python3 -c "import xml.dom.minidom,re,sys;[xml.dom.minidom.parseString(re.search(r'<svg.*?</svg>',open(f).read(),re.S).group(0)) for f in sys.argv[1:]]" A B`: el SVG es XML válido.
      - La línea del logo (`<img class="brand-logo" src="data:image/png;base64,`) mide 40126 caracteres en ambos: `awk 'length>2000{print length}'`.
      - Ningún otro archivo de docs/diagrams cambió de mtime: `ls -lT docs/diagrams`.
      Visual:
      - `agent-browser` abre `file://…/A` y `file://…/B` y toma una captura de cada uno a /tmp.
      - En las capturas, el verde domina (masthead, zonas, flechas, bordes de nodos y tarjetas) y el amarillo se ve claramente (badges, etiquetas, chips, nodos de clasificación, Power BI y alarma).
      - No hay azul ni ámbar, y ningún texto amarillo queda sobre fondo claro.
      - Borrar las capturas de /tmp al terminar.
      Files: ninguno.
      Verify: todo lo anterior se cumple. Hacer `git status` para confirmar que solo docs/diagrams sigue untracked y que no se creó ningún commit.
