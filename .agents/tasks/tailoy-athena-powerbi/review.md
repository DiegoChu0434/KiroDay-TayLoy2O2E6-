# Rama analítica Athena → Power BI en el flujo de alertas Tai Loy

El coder añadió una rama analítica al diagrama de flujo (`flujo-alertas-dataflow-full.html`): tras la Sintetizadora, el flujo ahora se bifurca en dos entregas. El correo accionable (SES) baja un carril para diferenciar el flujo operativo, y en paralelo nace una rama de datos (trazo diferenciado) hacia Athena y, de ahí, hacia Power BI vía ODBC. Para alojarlo se añadieron dos carriles nuevos (`ANALÍTICA · ATHENA` y `ENTREGA · BI · CORREO`), se amplió el `viewBox` de 456 a 616 px de alto y la leyenda se desplazó 160 px hacia abajo. El cambio llega junto a una re-paleta completa del archivo hacia los colores oficiales de marca.

Watch for: nada bloqueante. El criterio principal (Correo y Power BI al mismo nivel) se cumple de forma exacta — ambos nodos comparten `y=444` en el carril ENTREGA (confirmed). La re-paleta elimina por completo el azul `#1e4389` y los ámbar/azul-grisáceos previos; no quedan colores fuera de marca (confirmed).

**Verdict**: APPROVED

## High-level view

El criterio rector se cumple sin ambigüedad: Correo accionable y Power BI son nodos hermanos en el carril `ENTREGA`, ambos anclados en `y=444` con idéntica geometría de 100×64, de modo que están literalmente a la misma altura. Encima de ellos, Athena ocupa su propio carril `ANALÍTICA` (`y=364`), quedando entre la Sintetizadora (arriba) y Power BI (abajo), que es exactamente la topología pedida.

La bifurcación quedó bien expresada visualmente. De la Sintetizadora salen dos trazos distintos: uno punteado fino (2,2) que baja un carril hasta el Correo (flujo "entregado"), y otro discontinuo más marcado (5,3, marcador `arr-analytic-f`) que se desvía hacia Athena. Athena enlaza con Power BI con el mismo trazo analítico rotulado ODBC. La leyenda se amplió con la entrada "analítica · ODBC", así que el lenguaje visual es autoexplicativo.

La geometría encaja dentro del lienzo: el nodo más bajo (Power BI/Correo) termina en `y=508` y la leyenda desplazada cierra alrededor de `y=600`, todo por debajo del `viewBox` de 616. Las tarjetas y el footer son HTML que fluye tras el SVG, así que no hay riesgo de solape ni recorte.

La re-paleta es íntegramente de marca. El token `--color-link: #1e4389` (azul) se eliminó y los antiguos ámbar (`#b8915a`, `#9c6b50`), azul-grisáceo (`#5e7a9b`) y verdes neutros desafinados desaparecieron del SVG. Un grep del archivo final no devuelve ninguno de esos hex. Los nodos nuevos reutilizan los mismos patrones (relleno `#f6faf7`, borde `#008C4B`, chips de datos, badges de servicio) que los existentes, por lo que se ven hermanos. El nivel de abstracción se mantiene alto: Athena se describe como "tabla errores_detalle / Glue + Parquet · SQL" y Power BI como "4 páginas · Pareto / en vivo vía ODBC", sin bajar a pasos de DSN ni credenciales.

<details>
<summary>Issues (0)</summary>

No hay hallazgos accionables. Todos los criterios se cumplen.

</details>

<details>
<summary>Details</summary>

## Correo y Power BI al mismo nivel (criterio principal)

Confirmed. Ambos nodos se declaran con el mismo `y` y las mismas dimensiones:

```
Correo accionable:  <rect x="482" y="444" width="100" height="64" ...>
Power BI:           <rect x="594" y="444" width="100" height="64" ...>
```

Comparten carril `ENTREGA · BI · CORREO` (banda 436–516) y difieren solo en `x` (columna izquierda vs. derecha). No hay desfase vertical. El textos interno de cada nodo usa las mismas coordenadas relativas (título en `y=470`, metadatos en `482`/`494`, badge en `498`), así que son visualmente idénticos en altura. Esto es exactamente lo que el usuario repitió como lo que más importa.

## Topología de la rama analítica

Confirmed. Las posiciones verticales trazan la cadena pedida:

```
NOTIFICA (276–356)   Sintetizadora  y=284..348
ANALÍTICA (356–436)  Athena         y=364..428
ENTREGA  (436–516)   Correo  y=444   |   Power BI  y=444
```

Athena queda estrictamente entre la Sintetizadora (encima) y Power BI (debajo), en su propio carril. Correo bajó del carril NOTIFICA (donde estaba en `antes.png`, junto a la Sintetizadora) al carril ENTREGA, cumpliendo "Correo accionable debe bajar un nivel para diferenciar el flujo". La captura `despues.png` confirma visualmente los dos carriles nuevos con sus etiquetas y los cuatro nodos en las bandas correctas.

## Flechas y diferenciación de trazo

Confirmed. Tres aristas nuevas, con tres lenguajes de trazo:

```
Sintetizadora → Correo   M532,348 → 532,444   dash 2,2  (arr-link-f)      "entregado"
Sintetizadora → Athena   M582,316 → 644,364   dash 5,3  (arr-analytic-f)  rótulo CONSULTA
Athena        → Power BI  M644,428 → 644,444   dash 5,3  (arr-analytic-f)  rótulo ODBC
```

La rama analítica (5,3 + marcador `arr-analytic-f` nuevo, color `#006B39`) se distingue claramente del flujo de entrega del correo (punteado 2,2) y del hand-off/entrada-a-IA sólidos. Se añadió el marcador `arr-analytic-f` en `<defs>` y la leyenda FLUJO ganó la entrada "analítica · ODBC", así que el trazo diferenciado está documentado. En `despues.png` se ve la bifurcación saliendo de la Sintetizadora: punteado hacia abajo al Correo y discontinuo hacia la derecha a Athena, con los chips amarillos CONSULTA y ODBC.

## Encaje en el lienzo, sin solapes ni recortes

Confirmed. El `viewBox` pasó de `0 0 728 456` a `0 0 728 616` (+160, dos carriles de 80). Se añadieron las bandas de fondo, las líneas de carril en `y=436` y `y=516`, y la columna lateral se extendió a `y=516`. El elemento SVG más bajo (nodos Correo/Power BI) termina en `y=508`; el grupo de leyenda se envolvió en `<g transform="translate(0,160)">` y, partiendo de su `y≈440` original, cierra en torno a `y=600` — todo dentro de 616. Las tarjetas (`.cards`) y el footer son bloques HTML posteriores al contenedor del SVG, por lo que fluyen debajo sin posibilidad de solape; `despues.png` lo confirma: diagrama completo, luego las tres tarjetas, luego el footer.

## Paleta de marca

Confirmed. El cambio es una re-paleta total hacia los colores oficiales:

- Verde marca `#008C4B` (estructura, flujo, bordes), verde profundo `#006B39` (texto verde pequeño, fondos con texto blanco/amarillo), amarillo `#FFDA00` (resaltes como relleno).
- Neutros derivados del verde: ink `#0b2e1c`, muted `#2f6b4a`, soft `#4d8064`, rule `rgba(0,140,75,α)`, paper `#f6faf7`.

El token `--color-link: #1e4389` se eliminó del `:root` y el marcador `arr-link-f` ahora pinta `#006B39` en vez de azul. Un grep del archivo final por `1e4389`, `b8915a`, `9c6b50`, `5e7a9b`, `4a7c59`, `fafaf7`, `4a7a5f`, `7fae92` y `16,36,26` devuelve cero coincidencias: no sobrevive ningún color del esquema anterior ni ninguno fuera de marca. Los nodos nuevos (Athena, Power BI) usan `fill="#f6faf7"` + `stroke="#008C4B"` + badges amarillos, idénticos al patrón de los nodos preexistentes.

## Legibilidad del texto

Confirmed. El amarillo se usa solo como relleno de fondo con texto oscuro encima: chips RESUMEN JSON / CONSULTA / ODBC llevan `fill="#0b2e1c"` sobre `#FFDA00`; los badges AI/FL sobre fondo verde profundo usan amarillo como texto (`fill="#FFDA00"` sobre `#006B39`/`#0b2e1c`), que es alto contraste. No hay texto amarillo sobre fondo claro. Los textos de metadatos de los nodos nuevos usan `#2f6b4a` y `#4d8064` sobre `#f6faf7`, el mismo contraste que el resto del diagrama.

## Consistencia de estilo y nivel de abstracción

Confirmed. Athena y Power BI replican la plantilla de nodo: rect 100×64 `rx=6`, badge de servicio arriba-izquierda (ATH, BI), título en sans 9px, dos líneas de metadatos en mono 6.5px, y chip de datos TB abajo-derecha. Encajan como hermanos de S3/CW/Sintetizadora. El contenido se mantiene a nivel de presentación ejecutiva: "tabla errores_detalle", "Glue + Parquet · SQL", "4 páginas · Pareto", "en vivo vía ODBC". No aparecen pasos de instalación de driver, DSN `Athena_TaiLoy` ni manejo de credenciales — justo lo que el usuario pidió ("hagamoslo para una presentacion alto nivel").

## Alcance del cambio

Confirmed para este trabajo. `git status` muestra cinco archivos modificados, pero `arquitectura-aws-full.html`, `infraestructura-desplegada.md`, `cloudformation.yaml` y `email_formatter.py` corresponden a trabajo previo/paralelo (re-paleta del otro diagrama e infra ya desplegada), explícitamente marcados como esperados y fuera del alcance de esta revisión. El único archivo que esta tarea debía tocar — `flujo-alertas-dataflow-full.html` — es el que contiene la rama analítica. El logo en base64 no aparece en el diff (cero líneas `base64` añadidas/eliminadas), por lo que quedó intacto.

</details>

<details>
<summary>Mapa de archivos</summary>

- `docs/diagrams/flujo-alertas-dataflow-full.html` — único archivo en alcance: rama analítica Athena→Power BI, Correo bajado un carril, re-paleta a colores de marca, viewBox 456→616, leyenda desplazada +160.
- (fuera de alcance, trabajo previo esperado) `docs/diagrams/arquitectura-aws-full.html`, `docs/infraestructura-desplegada.md`, `infra/cloudformation.yaml`, `src/email_formatter/email_formatter.py`.

Diff completo: `git diff docs/diagrams/flujo-alertas-dataflow-full.html`

</details>
