#!/usr/bin/env python3
"""Aplica la paleta Tai Loy (plan.md) a los 2 diagramas *-full.html.

Edita por número de línea ORIGINAL (baseline) con reemplazos exactos y
verificados (assert): si una línea no contiene lo esperado, aborta sin escribir.
Nunca toca la línea del logo base64. Lee siempre desde baseline/ para que
sea idempotente.
"""
import hashlib
import pathlib

ROOT = pathlib.Path("/Users/diego/Documents/BigCheese/KiroDay/KiroDay-TayLoy")
TASK = ROOT / ".agents/tasks/tailoy-colores"
LOGO_SHA = "379d7386385b695253e7143fecf71131950517a21c17a40a1ab58943615f1ea1"

ROOT_CSS = """    :root {
      /* Tai Loy · colores oficiales de marca
         Digital:   Verde R0 G140 B75 #008C4B  · Amarillo R255 G218 B0 #FFDA00
         Impresión: Verde C100 M10 Y100 K10    · Amarillo C0 M12 Y100 K0
         Neutros (ink/muted/soft/rule) derivados del matiz del verde de marca.
         El SVG inline usa estos mismos hex literales: si cambias un token, cámbialo también allí. */
      --color-paper:       #f6faf7;
      --color-paper-2:     #e6f3ec;
      --color-ink:         #0b2e1c;
      --color-muted:       #2f6b4a;
      --color-soft:        #4d8064;
      --color-rule:        rgba(0,140,75,0.25);
      --color-accent:      #008C4B; /* verde marca: estructura, flujo, bordes */
      --color-accent-deep: #006B39; /* verde profundo: texto verde pequeño y fondos con texto blanco/amarillo */
      --color-accent-tint: rgba(0,140,75,0.10);
      --color-yellow:      #FFDA00; /* amarillo marca: resaltes, siempre como relleno */
      --color-yellow-tint: rgba(255,218,0,0.28);
      --color-on-accent:   #ffffff;
      --font-sans:  'Roboto', 'Geist', system-ui, sans-serif;
      --font-serif: 'Instrument Serif', serif;
      --font-mono:  'Roboto Mono', 'Geist Mono', ui-monospace, monospace;
    }"""

# Reemplazos globales de neutros (se aplican a todas las líneas salvo logo,
# DESPUÉS de los reemplazos por línea).
GLOBAL = [
    ("#10241a", "#0b2e1c"),
    ("#4a7a5f", "#2f6b4a"),
    ("#7fae92", "#4d8064"),
    ("#fafaf7", "#f6faf7"),
]

FW7 = ('font-weight="500"', 'font-weight="700"')


def css_rules(masthead_margin):
    mh_extra = " margin-bottom: 2.5rem;" if masthead_margin else ""
    return {
        "eyebrow": ("color: var(--color-muted); margin-bottom: 0.75rem; }",
                    "color: var(--color-ink); margin-bottom: 0.75rem; display: inline-block; background: var(--color-yellow); padding: 0.3rem 0.55rem; border-radius: 3px; font-weight: 600; }"),
        "h1": ("line-height: 1.1; color: var(--color-ink);", "line-height: 1.1; color: var(--color-on-accent);"),
        "bb1": (".brand-bar span:first-child { width: 68px; background: var(--color-accent); }",
                ".brand-bar span:first-child { width: 68px; background: var(--color-yellow); }"),
        "bb2": (".brand-bar span:last-child { width: 24px; background: var(--color-yellow); }",
                ".brand-bar span:last-child { width: 24px; background: #ffffff; }"),
        "masthead": (f".masthead {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 2rem;{mh_extra} }}",
                     f".masthead {{ display: flex; align-items: center; justify-content: space-between; gap: 2rem;{mh_extra} background: var(--color-accent-deep); border-top: 8px solid var(--color-accent); border-bottom: 6px solid var(--color-yellow); border-radius: 10px; padding: 1.75rem 2rem; }}"),
        "logo": ("border-radius: 12px; display: block; }", "border-radius: 12px; display: block; box-shadow: 0 0 0 3px var(--color-yellow); }"),
        "subtitle": ("line-height: 1.55; color: var(--color-muted);", "line-height: 1.55; color: #ffffff;"),
        "card": ("border: 1px solid var(--color-rule); padding: 1.25rem; }",
                 "border: 1px solid var(--color-rule); border-top: 4px solid var(--color-accent); padding: 1.25rem; }"),
        "cardh": ("border-bottom: 1px solid rgba(16,36,26,0.08); }", "border-bottom: 1px solid rgba(0,140,75,0.25); }"),
        "h3": ("font-weight: 600; color: var(--color-ink);", "font-weight: 600; color: var(--color-accent-deep);"),
        "li": ("color: rgba(16,36,26,0.25);", "color: var(--color-accent);"),
        "footer": ("border-top: 1px solid rgba(16,36,26,0.10);", "border-top: 2px solid var(--color-accent);"),
        "footer2": ("color: var(--color-soft);", "color: var(--color-muted);"),
    }


def flujo_edits():
    r = css_rules(masthead_margin=False)
    e = {
        27: [r["eyebrow"]], 28: [r["h1"]], 31: [r["bb1"]], 32: [r["bb2"]],
        33: [r["masthead"]], 35: [r["logo"]], 36: [r["subtitle"]],
        41: [r["card"]], 42: [r["cardh"]],
        46: [(".card-dot.link { background: var(--color-link); }",
              ".card-dot.link { background: var(--color-yellow); box-shadow: 0 0 0 1.5px var(--color-accent-deep); }")],
        47: [r["h3"]], 50: [r["li"]], 52: [r["footer"], r["footer2"]],
        # defs
        73: [("rgba(16,36,26,0.10)", "rgba(0,140,75,0.16)")],
        75: [("#4a7a5f", "#008C4B")],
        77: [("#1e4389", "#006B39")],
        # bandas y grilla
        84: [("rgba(16,36,26,0.018)", "rgba(0,140,75,0.05)")],
        85: [("rgba(16,36,26,0.018)", "rgba(0,140,75,0.05)")],
        # pasos
        103: [('fill="rgba(0,140,75,0.20)"', 'fill="#006B39"')],
        104: [('fill="#008C4B"', 'fill="#FFDA00"')],
        105: [('font-weight="500"', 'font-weight="700"'), ('fill="#008C4B"', 'fill="#006B39"')],
        # flechas
        119: [("#4a7a5f", "#008C4B")], 120: [("#4a7a5f", "#008C4B")],
        121: [('stroke-width="1.4"', 'stroke-width="2"')],
        # backplate ahora visible (amarillo): se ensancha para cubrir el texto
        # "RESUMEN JSON" (antes era invisible sobre el fondo y el texto lo desbordaba)
        122: [('x="540" y="250" width="54"', 'x="534" y="250" width="66"'), ('fill="#fafaf7"', 'fill="#FFDA00"')],
        123: [('fill="#008C4B"', 'font-weight="700" fill="#0b2e1c"')],
        124: [('stroke="#1e4389" stroke-width="1"', 'stroke="#006B39" stroke-width="1" stroke-dasharray="2,2"')],
        # nodos neutros
        126: [("rgba(16,36,26,0.25)", "rgba(0,140,75,0.55)")],
        127: [("rgba(16,36,26,0.12)", "rgba(0,140,75,0.14)")],
        146: [("rgba(16,36,26,0.25)", "rgba(0,140,75,0.55)")],
        147: [("rgba(16,36,26,0.12)", "rgba(0,140,75,0.14)")],
        # chips de datos
        132: [("#5e7a9b", "#006B39")], 141: [("#5e7a9b", "#006B39")],
        143: [("#b8915a", "#FFDA00")], 144: [('fill="#fff"', 'fill="#0b2e1c"')],
        152: [("#b8915a", "#FFDA00")], 153: [('fill="#fff"', 'fill="#0b2e1c"')],
        154: [("#4a7c59", "#008C4B")], 163: [("#4a7c59", "#008C4B")],
        165: [("#9c6b50", "#0b2e1c")], 166: [('fill="#fff"', 'fill="#FFDA00"')],
        174: [("#9c6b50", "#0b2e1c")], 175: [('fill="#fff"', 'fill="#FFDA00"')],
        # Analizadora (clasificación, amarillo)
        135: [("rgba(94,122,155,0.06)", "rgba(255,218,0,0.22)"), ("rgba(94,122,155,0.35)", "#008C4B")],
        136: [("rgba(94,122,155,0.18)", "#FFDA00")],
        137: [("#5e7a9b", "#0b2e1c")], 138: [("#5e7a9b", "#0b2e1c")],
        # Sintetizadora (focal)
        157: [("rgba(0,140,75,0.07)", "rgba(0,140,75,0.14)"), ('stroke-width="1.4"', 'stroke-width="1.8"')],
        158: [("rgba(0,140,75,0.20)", "#006B39")],
        159: [('fill="#008C4B"', 'fill="#FFDA00"')],
        # SES
        168: [("rgba(30,67,137,0.4)", "#008C4B")],
        169: [("rgba(30,67,137,0.18)", "#FFDA00")],
        170: [("#1e4389", "#0b2e1c")], 171: [("#1e4389", "#006B39")],
        # leyenda
        177: [FW7, ("#7fae92", "#006B39")], 184: [FW7, ("#7fae92", "#006B39")],
        191: [FW7, ("#7fae92", "#006B39")], 195: [FW7, ("#7fae92", "#006B39")],
        181: [('fill="#008C4B"', 'fill="#006B39"')],
        185: [("#5e7a9b", "#006B39")], 186: [("#b8915a", "#FFDA00")],
        187: [("#4a7c59", "#008C4B")], 188: [("#9c6b50", "#0b2e1c")],
        192: [('fill="rgba(94,122,155,0.5)"', 'fill="#FFDA00" stroke="#008C4B" stroke-width="0.6"')],
        193: [('font-size="7" fill="#008C4B"', 'font-size="7" fill="#006B39"')],
        196: [('stroke="#4a7a5f"', 'stroke="#008C4B"')],
        197: [('stroke-width="1.4"', 'stroke-width="2"'), ('font-size="7" fill="#008C4B"', 'font-size="7" font-weight="700" fill="#006B39"')],
        198: [('stroke="#1e4389" stroke-width="1"', 'stroke="#006B39" stroke-width="1" stroke-dasharray="2,2"'),
              ('fill="#1e4389"', 'fill="#006B39"')],
    }
    for n in range(87, 93):
        e[n] = [("rgba(16,36,26,0.12)", "rgba(0,140,75,0.25)")]
    for n in (94, 97, 100, 106):
        e[n] = [('fill="rgba(16,36,26,0.12)"', 'fill="#FFDA00"')]
    for n in (96, 99, 102, 108):
        e[n] = [("#4a7a5f", "#006B39")]
    for n in range(110, 118):
        e[n] = [("#4a7a5f", "#006B39")]
    inserts = {81: ['        <rect x="0" y="0" width="728" height="36" fill="rgba(0,140,75,0.10)"/>',
                    '        <rect x="0" y="36" width="140" height="320" fill="rgba(0,140,75,0.08)"/>']}
    return e, inserts


def arq_edits():
    r = css_rules(masthead_margin=True)
    e = {
        26: [r["eyebrow"]], 27: [r["h1"]], 30: [r["bb1"]], 31: [r["bb2"]],
        32: [r["subtitle"]], 33: [r["masthead"]], 35: [r["logo"]],
        40: [r["card"]], 41: [r["cardh"]],
        45: [(".card-dot.amber { background: #b8915a; }",
              ".card-dot.amber { background: var(--color-yellow); box-shadow: 0 0 0 1.5px var(--color-accent-deep); }")],
        46: [r["h3"]], 49: [r["li"]], 51: [r["footer"], r["footer2"]],
        # defs
        72: [("rgba(16,36,26,0.10)", "rgba(0,140,75,0.16)")],
        74: [("#4a7a5f", "#008C4B")], 76: [("#1e4389", "#006B39")], 77: [("#b8915a", "#4d8064")],
        # cuenta y zonas
        84: [("rgba(16,36,26,0.22)", "rgba(0,140,75,0.6)")],
        85: [('fill="#fafaf7"', 'fill="#FFDA00"')],
        86: [('fill="#4a7a5f"', 'fill="#0b2e1c"'), ('font-weight="500"', 'font-weight="700"')],
        # flechas
        108: [('stroke-width="1.6"', 'stroke-width="2.2"')],
        112: [('stroke="#1e4389" stroke-width="1.2"', 'stroke="#006B39" stroke-width="1.2" stroke-dasharray="2,2"')],
        131: [('stroke="#1e4389" stroke-width="1.2"', 'stroke="#006B39" stroke-width="1.2" stroke-dasharray="2,2"')],
        124: [("#b8915a", "#4d8064")],
        # focal
        165: [("rgba(0,140,75,0.08)", "rgba(0,140,75,0.14)"), ('stroke-width="1.4"', 'stroke-width="1.8"')],
        166: [('fill="transparent" stroke="rgba(0,140,75,0.5)"', 'fill="#006B39" stroke="#006B39"')],
        167: [('fill="#008C4B"', 'fill="#FFDA00"')],
        # SES
        174: [("rgba(30,67,137,0.05)", "rgba(255,218,0,0.18)"), ("rgba(30,67,137,0.5)", "#008C4B")],
        175: [("rgba(30,67,137,0.4)", "#008C4B")],
        176: [("#1e4389", "#006B39")],
        # Bedrock
        183: [("rgba(0,140,75,0.05)", "rgba(0,140,75,0.10)"), ("rgba(0,140,75,0.45)", "#008C4B")],
        # CloudWatch Alarm
        189: [("rgba(184,145,90,0.08)", "rgba(255,218,0,0.28)"), ("rgba(184,145,90,0.5)", "#008C4B")],
        # Power BI
        223: [("rgba(255,212,0,0.14)", "rgba(255,218,0,0.30)"), ("rgba(184,145,90,0.6)", "#008C4B")],
        224: [('fill="transparent" stroke="rgba(184,145,90,0.5)"', 'fill="#FFDA00" stroke="#008C4B"')],
        225: [("#b8915a", "#0b2e1c")],
        # leyenda
        231: [("rgba(16,36,26,0.45)", "#006B39"), FW7],
        232: [("rgba(0,140,75,0.08)", "rgba(0,140,75,0.14)")],
        236: [('stroke="#1e4389" stroke-width="1.2"', 'stroke="#006B39" stroke-width="1.2" stroke-dasharray="2,2"')],
        238: [("#b8915a", "#4d8064")],
        240: [("rgba(16,36,26,0.22)", "rgba(0,140,75,0.6)")],
    }
    for n in (89, 94):
        e[n] = [("rgba(16,36,26,0.02)", "rgba(0,140,75,0.05)"), ("rgba(16,36,26,0.10)", "rgba(0,140,75,0.40)")]
    for n in (90, 95):
        e[n] = [('fill="#fafaf7"', 'fill="#006B39"')]
    for n in (91, 96):
        e[n] = [('fill="rgba(16,36,26,0.45)"', 'fill="#FFDA00" font-weight="700"')]
    for n in (100, 104, 119, 129, 130):
        e[n] = [('stroke="#4a7a5f"', 'stroke="#008C4B"')]
    for n in (101, 105, 109, 113, 120, 125, 132):
        e[n] = [('fill="#fafaf7"', 'fill="#FFDA00"')]
    for n in (102, 106, 110, 114, 121, 126, 133):
        e[n] = [("fill=\"#4a7a5f\"", 'fill="#0b2e1c" font-weight="700"'),
                ("fill=\"#008C4B\"", 'fill="#0b2e1c" font-weight="700"'),
                ("fill=\"#1e4389\"", 'fill="#0b2e1c" font-weight="700"'),
                ("fill=\"#b8915a\"", 'fill="#0b2e1c" font-weight="700"')]
    for n in (138, 147, 156, 196, 205, 214):
        e[n] = [("rgba(16,36,26,0.03)", "rgba(0,140,75,0.05)"), ("rgba(16,36,26,0.30)", "rgba(0,140,75,0.55)")]
    for n in (139, 148, 157, 197, 206, 215):
        e[n] = [('fill="transparent" stroke="rgba(16,36,26,0.25)"', 'fill="rgba(0,140,75,0.12)" stroke="rgba(0,140,75,0.5)"')]
    for n in (140, 149, 158, 198, 207, 216):
        e[n] = [('fill="#4a7a5f"', 'fill="#006B39"')]
    return e, {}


def apply(name, edits, inserts, optional_lines=()):
    src = (TASK / "baseline" / name).read_text(encoding="utf-8")
    lines = src.split("\n")
    out = []
    for i, line in enumerate(lines, start=1):
        if 'class="brand-logo"' in line and len(line) > 2000:
            assert hashlib.sha256((line + "\n").encode()).hexdigest() == LOGO_SHA, "logo cambió"
            out.append(line)
            continue
        if 10 <= i <= 23:  # bloque :root original
            if i == 10:
                assert lines[9].strip() == ":root {" and lines[22].strip() == "}"
                out.append(ROOT_CSS)
            continue
        for old, new in edits.get(i, []):
            if old in line:
                line = line.replace(old, new)
            elif i not in optional_lines:
                raise SystemExit(f"{name}:{i}: no contiene {old!r}\n  {line}")
        for old, new in GLOBAL:
            line = line.replace(old, new)
        out.append(line)
        out.extend(inserts.get(i, []))
    (ROOT / "docs/diagrams" / name).write_text("\n".join(out), encoding="utf-8")
    print("ok", name)


if __name__ == "__main__":
    e, ins = flujo_edits()
    apply("flujo-alertas-dataflow-full.html", e, ins)
    e, ins = arq_edits()
    # líneas de texto de etiqueta en arquitectura: solo uno de los 4 fills aplica
    apply("arquitectura-aws-full.html", e, ins,
          optional_lines=(102, 106, 110, 114, 121, 126, 133))
