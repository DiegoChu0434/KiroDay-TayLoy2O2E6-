# Code notes: paleta Tai Loy dominante (iteración 1)

No había `review.json`, así que esta es la primera iteración. Seguí la versión vigente de `plan.md` (11270 bytes, 14:35). El planner la reescribió mientras yo empezaba; en esa versión A = flujo y B = arquitectura.

## Qué se hizo

- Los cambios se aplicaron con `apply_palette.py`, que está en esta carpeta.
  - Lee siempre desde `baseline/`, así que se puede volver a ejecutar sin efectos acumulados.
  - Edita por número de línea original con reemplazos exactos. Si una línea no contiene lo esperado, aborta sin escribir.
  - Antes de escribir comprueba que el SHA-256 de la línea del logo sigue siendo `379d73…1ea1`.
  - Al final aplica 4 reemplazos globales de neutros: `#10241a→#0b2e1c`, `#4a7a5f→#2f6b4a`, `#7fae92→#4d8064` y `#fafaf7→#f6faf7`.
- Los dos archivos tienen el mismo bloque `:root`, con los tokens de la tabla de abajo y un comentario con los equivalentes digital/CMYK. Se eliminó `--color-link`.
- CSS común:
  - Masthead: banda `#006B39` con borde superior de 8px en `#008C4B` y borde inferior de 6px en `#FFDA00`. h1 y subtítulo en blanco.
  - Eyebrow: chip amarillo con texto ink.
  - Brand-bar: amarillo + blanco.
  - Logo: anillo amarillo de 3px.
  - Tarjetas: borde superior de 4px en verde y h3 en `#006B39`.
  - Viñetas de lista en verde.
  - `card-dot.link` (flujo) y `card-dot.amber` (arquitectura): punto amarillo con anillo verde. Los nombres de clase no se tocaron.
  - Footer: borde de 2px en verde y texto muted.
- SVG: solo cambian fill, stroke, stroke-width, stroke-dasharray y font-weight, según el plan. Hay 3 excepciones de geometría, todas en fondos:
  1. En flujo se insertaron 2 rects de fondo después de `url(#dots-full)`, como pide el plan: la franja de cabecera `0,0,728×36` y la banda de carriles `0,36,140×320`.
  2. En flujo se ensanchó el backplate de "RESUMEN JSON" de `x=540 w=54` a `x=534 w=66`. Antes era invisible sobre el fondo y el texto ya lo desbordaba; al pasar a amarillo se veía el texto saliéndose del chip. El texto y su posición no cambian.
  3. En arquitectura, el swatch focal de la leyenda pasa a `rgba(0,140,75,0.14)` para que coincida con el nodo focal. Es solo color.
- No se cambió ningún texto, coordenada de nodo ni flecha, ni la tipografía. No se tocó el base64 del logo. No hay commits.

## Mapa de color (rol → color), igual en ambos diagramas

| Rol | Color |
|---|---|
| paper (fondo) / paper-2 | `#f6faf7` / `#e6f3ec` |
| ink (texto principal) | `#0b2e1c` |
| muted (texto secundario) | `#2f6b4a` |
| soft (texto terciario, flecha pendiente) | `#4d8064` |
| rule / grilla | `rgba(0,140,75,0.25)` |
| Estructura: flechas de flujo, bordes de nodos/zonas, borde de tarjetas, franja del masthead | `#008C4B` |
| Verde profundo: banda del masthead, texto verde pequeño, chips con texto blanco o amarillo, entrega | `#006B39` |
| Amarillo: pills de paso 01/02/03/05, backplates de etiquetas de flecha, eyebrow, chips TB/SES/λ/BI, borde inferior del masthead, anillo del logo, card-dot de resultado/estado | `#FFDA00` (siempre como relleno) |
| Tinte amarillo: Analizadora (flujo); CloudWatch Alarm, Power BI y SES (arquitectura) | `rgba(255,218,0,0.18–0.30)` |
| Nodo focal (Sintetizadora) | relleno `rgba(0,140,75,0.14)`, borde `#008C4B` 1.8, chip AI `#006B39` con texto `#FFDA00` |
| Paso focal 04 | pill `#006B39` con número `#FFDA00`, etiqueta en negrita `#006B39` |
| Zonas (arquitectura) | relleno `rgba(0,140,75,0.05)`, borde `0.40`, etiqueta en chip `#006B39` con texto amarillo bold |
| Frontera de la cuenta AWS | `rgba(0,140,75,0.6)` discontinuo, etiqueta en chip `#FFDA00` con texto ink bold |
| Chips de datos (flujo) | DB `#006B39`/blanco · TB `#FFDA00`/ink · LS `#008C4B`/blanco · FL `#0b2e1c`/amarillo |

Cómo se distinguen los estados, sin colores ajenos:

| Estado | Trazo |
|---|---|
| Flujo | `#008C4B` sólido |
| Focal | verde más grueso (2 / 2.2) con etiqueta amarilla |
| Métricas | verde con trazo `4,3` |
| Entrega / consulta externa (SEND, ODBC, entregado) | `#006B39` con trazo `2,2` |
| Pendiente | `#4d8064` con trazo `5,4` |

Las leyendas se actualizaron para que coincidan.

## Accesibilidad

| Combinación | Contraste | Dónde se usa |
|---|---|---|
| Blanco sobre `#006B39` | ≈6.6:1 | subtítulo y h1 |
| `#FFDA00` sobre `#006B39` | ≈4.8:1 | etiquetas de zona, número 04, chip AI |
| Ink sobre `#FFDA00` | — | chips y etiquetas |

Ningún texto amarillo queda sobre fondo claro. El texto `#008C4B` sobre blanco no se usa en texto pequeño, que va en `#006B39`.

Excepción conocida, heredada del plan: el chip "LS" usa `#008C4B` con texto blanco (≈4.3:1, letra de 5px). Es un rótulo de 2 letras con equivalente en la leyenda.

## Capturas (Chrome headless, 1440×1800)

| Diagrama | Antes | Después |
|---|---|---|
| Flujo | `/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/.agents/tasks/tailoy-colores/flujo-antes.png` | `/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/.agents/tasks/tailoy-colores/flujo-despues.png` |
| Arquitectura | `/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/.agents/tasks/tailoy-colores/arquitectura-antes.png` | `/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy/.agents/tasks/tailoy-colores/arquitectura-despues.png` |

Revisión visual de las capturas:

- El verde domina en el masthead, los bordes, las flechas, los carriles y las zonas.
- El amarillo se ve con fuerza en los pills, las etiquetas de flecha, la Analizadora, las alarmas, Power BI, SES, el eyebrow y los chips.
- No queda azul ni ámbar.
- El layout es idéntico al de las capturas "antes".
- No hay texto ilegible ni desbordado.

## Verificación

- `grep -Eic '#1e4389|#b8915a|rgba\(94,122,155|rgba\(30,67,137'` da 0 en ambos archivos.
- El grep ampliado, que además busca `30,67,137`, `184,145,90`, `5e7a9b`, `4a7c59`, `9c6b50`, `255,212,0`, `16,36,26`, los neutros viejos y `color-link`, también da 0 en ambos.
- Fuera de la línea del logo solo quedan colores de la paleta: `#006b39 #008c4b #0b2e1c #2f6b4a #4d8064 #e6f3ec #f6faf7 #ffda00 #fff #ffffff`, `rgba(0,140,75,…)` y `rgba(255,218,0,…)`.
- Línea del logo: el SHA-256 coincide con el original en ambos archivos (`379d73…1ea1`) y la longitud es 40126 en ambos.
- El HTML parsea sin errores y el `<svg>` es XML válido en ambos.
- `shasum -c baseline/siblings.sha256` da todo OK. Las variantes `-dark`, las base y los `.png`/`.svg` no cambiaron.
- `git status --porcelain`:
  ```
   M docs/diagrams/arquitectura-aws-full.html        ← mío
   M docs/diagrams/flujo-alertas-dataflow-full.html  ← mío
   M docs/infraestructura-desplegada.md              ← NO mío (mtime 14:39:22, editado por otro proceso durante la sesión; no lo toqué ni lo revertí)
   M infra/cloudformation.yaml                       ← NO mío (ya estaba modificado antes de empezar, mtime 14:30:57)
  ?? .agents/
  ```
  Los dos HTML no tenían cambios previos sin commitear: `cmp` con `baseline/` dio idéntico antes de aplicar. El último commit sigue siendo `41f9a39`.
