"""
Lambda SINTETIZADORA de correo (integración AS/400 -> SAP).

Se suscribe al topic SNS que publica la Lambda analizadora. Toma el resumen
del lote (JSON), calcula/renderiza las cifras de forma determinista en código y
usa Amazon Bedrock (Claude Sonnet 5.5) SOLO para redactar la narrativa
(resumen ejecutivo + próxima acción sugerida). Ensambla y envía UN único correo
por SES.

Patrón híbrido (regla de oro):
  - El CÓDIGO manda los números: totales, conteos, %, top clientes, severidades,
    sección de stock. Todo sale del JSON del analizador (determinista, auditable).
  - La IA REDACTA: resumen ejecutivo (2-4 frases) y próxima acción por equipo.
    En el prompt se le pasan las cifras ya calculadas y se le prohíbe inventar otras.

Resiliencia:
  - Si Bedrock falla / da timeout / devuelve vacío, se cae a una narrativa
    plantillada (determinista). La alerta NUNCA se bloquea por la IA.

Datos técnicos validados en la PoC (cuenta 971431176203, us-east-1):
  - Invocar SIEMPRE el inference profile 'us.anthropic.claude-sonnet-5-5'.
    El modelId plano 'anthropic.claude-sonnet-5-5' falla con ValidationException
    (on-demand throughput isn't supported) + explicit deny de un SCP de la org.
  - Sonnet 5.5 DEPRECÓ 'temperature' (y top_p): en inferenceConfig solo 'maxTokens'.
  - La respuesta puede traer bloques 'reasoningContent'; al parsear
    output.message.content hay que quedarse solo con los bloques con clave 'text'.

Variables de entorno:
  SES_SENDER      remitente verificado en SES (obligatorio)
  SES_RECIPIENT   destinatario(s) (obligatorio). Uno o varios correos separados
                  por coma: "a@dom.com,b@dom.com". Todos reciben el mismo correo.
  MODEL_ID        inference profile Bedrock (default us.anthropic.claude-sonnet-5-5)
  BEDROCK_MAX_TOKENS  tope de tokens de salida (default 2000; Sonnet 5.5 consume
                      presupuesto en reasoning, por eso no bajar de ~1500)
  AWS_REGION      región (la inyecta Lambda automáticamente)
"""

import json
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client("ses")

# Cliente Bedrock con timeouts por DEBAJO del timeout de la Lambda (30 s).
_bedrock_cfg = Config(
    connect_timeout=3,
    read_timeout=12,
    retries={"max_attempts": 1},
)
bedrock = boto3.client("bedrock-runtime", config=_bedrock_cfg)

SES_SENDER = os.environ.get("SES_SENDER", "")
# SES_RECIPIENT admite uno o varios correos separados por coma (y/o punto y coma).
SES_RECIPIENT = os.environ.get("SES_RECIPIENT", "")
RECIPIENTS = [r.strip() for r in SES_RECIPIENT.replace(";", ",").split(",") if r.strip()]
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-5-5")
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2000"))
# Logo embebido (CID). Empaquetado junto al codigo de la Lambda.
LOGO_PATH = os.environ.get("LOGO_PATH", os.path.join(os.path.dirname(__file__), "tailoy-logo.png"))
LOGO_CID = "tailoy_logo"

# Paleta corporativa Tai Loy (identidad de marca)
BRAND_GREEN = "#008C4B"
BRAND_GREEN_DARK = "#00703C"
BRAND_YELLOW = "#FFDA00"

# Colores de severidad: mantienen su SEMANTICA de alerta (urgencia), no la marca.
# Un error CRITICO debe leerse como alarma, no como "todo bien".
SEVERIDAD_COLOR = {
    "CRITICA": "#c0392b",   # rojo = urgente
    "WARNING": "#e38a00",   # ambar (armoniza con el amarillo de marca)
    "INFO": "#5a6b62",      # gris-verde neutro
}

SYSTEM_PROMPT = (
    "Eres un asistente de operaciones de datos maestros de Tai Loy que redacta "
    "alertas accionables para los equipos responsables de la integración AS/400 -> SAP. "
    "Escribe en español, tono profesional y directo. NUNCA inventes ni recalcules "
    "cifras: usa EXCLUSIVAMENTE los números que se te entregan."
)


# ---------------------------------------------------------------------------
# NARRATIVA IA (Bedrock) con fallback determinista
# ---------------------------------------------------------------------------
def _build_prompt(summary):
    """Construye el prompt de usuario con las cifras y runbooks ya calculados."""
    lote = summary["lote"]
    cats = "; ".join(
        f"{c['categoria']}={c['conteo']} ({c['severidad']}, responsable "
        f"{c.get('responsable', {}).get('actor', '-')}/"
        f"{c.get('responsable', {}).get('frente', '-')})"
        for c in summary["categorias"]
    )
    return (
        "Datos del lote (NO los modifiques):\n"
        f"- Total de errores: {lote['total_errores']}\n"
        f"- Clientes afectados: {lote['clientes_afectados']}\n"
        f"- Categorías: {cats}\n"
        f"- Stock/ATP (alerta diferenciada): {summary.get('alerta_stock', {}).get('conteo', 0)}\n\n"
        "Redacta en español, en texto plano, dos secciones breves:\n"
        "1) RESUMEN EJECUTIVO: 2-4 frases sobre la salud del lote y lo más urgente.\n"
        "2) PRÓXIMA ACCIÓN: una viñeta por área responsable con la acción concreta.\n"
        "No inventes cifras ni procedimientos. No incluyas tablas. Máximo 180 palabras."
    )


def narrativa_fallback(summary):
    """Narrativa determinista de respaldo si Bedrock no está disponible."""
    cats = summary["categorias"]
    criticas = [c for c in cats if c["severidad"] == "CRITICA"]
    total = summary["lote"]["total_errores"]
    clientes = summary["lote"]["clientes_afectados"]

    partes = [
        f"RESUMEN EJECUTIVO: El lote presenta {total} errores que afectan a "
        f"{clientes} clientes. "
    ]
    if criticas:
        top = max(criticas, key=lambda c: c["conteo"])
        partes.append(
            f"La causa crítica predominante es {top['categoria']} "
            f"({top['conteo']} casos), responsabilidad de {top['equipo']}."
        )
    else:
        partes.append("No hay categorías críticas en este lote.")

    partes.append("\n\nPRÓXIMA ACCIÓN:")
    equipos = {}
    for c in cats:
        equipos.setdefault(c["equipo"], []).append(c)
    for equipo, lista in equipos.items():
        detalle = ", ".join(f"{c['categoria']} ({c['conteo']})" for c in lista)
        partes.append(f"\n- {equipo}: revisar {detalle}.")
    return "".join(partes)


def narrativa_ia(summary):
    """
    Llama a Bedrock para redactar la narrativa. Si algo falla, cae al fallback.
    Devuelve (texto, origen) donde origen es 'IA' o 'fallback'.
    """
    try:
        resp = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": _build_prompt(summary)}]}],
            inferenceConfig={"maxTokens": BEDROCK_MAX_TOKENS},  # sin 'temperature' (deprecado en 5.5)
        )
        # La respuesta puede incluir bloques reasoningContent: tomar solo los de texto.
        bloques = resp.get("output", {}).get("message", {}).get("content", [])
        texto = "".join(b["text"] for b in bloques if "text" in b).strip()
        if not texto:
            raise ValueError("Bedrock devolvió texto vacío.")
        logger.info("Narrativa IA generada. usage=%s", resp.get("usage"))
        return texto, "IA"
    except Exception as exc:  # noqa: BLE001 - la alerta nunca debe bloquearse por IA
        logger.warning("Bedrock no disponible (%s); usando narrativa de respaldo.", exc)
        return narrativa_fallback(summary), "fallback"


def _narrativa_html(texto, origen):
    etiqueta = (
        "redactado por IA (Bedrock / Claude Sonnet 5.5)"
        if origen == "IA"
        else "generado por plantilla de respaldo"
    )
    cuerpo = texto.replace("\n", "<br>")
    return (
        f"<div style='background:#f4faf6;border-left:4px solid {BRAND_GREEN};"
        "padding:12px 14px;margin:12px 0;border-radius:4px'>"
        f"<div style='font-size:14px;line-height:1.5'>{cuerpo}</div>"
        f"<div style='color:#8a9a91;font-size:11px;margin-top:8px'>{etiqueta}</div>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# RENDERIZADO DETERMINISTA (código manda los números)
# ---------------------------------------------------------------------------
def _row_categoria(c):
    color = SEVERIDAD_COLOR.get(c["severidad"], "#555")
    return (
        "<tr>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{c['categoria']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{c['conteo']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>"
        f"<span style='color:#fff;background:{color};padding:2px 8px;border-radius:3px;font-size:12px'>{c['severidad']}</span></td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{c['equipo']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{c['clientes_afectados']}</td>"
        "</tr>"
    )


def _row_cliente(c):
    cats = ", ".join(f"{k} ({v})" for k, v in c["categorias"].items())
    return (
        "<tr>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{c['cliente']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{c['total']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{cats}</td>"
        "</tr>"
    )


def _runbooks_html(summary):
    """Sección determinista con el procedimiento de solución por causa raíz."""
    bloques = []
    for c in summary["categorias"]:
        sol = c.get("solucion")
        if not sol:
            continue
        color = SEVERIDAD_COLOR.get(c["severidad"], "#555")
        pasos = "".join(f"<li style='margin:2px 0'>{p}</li>" for p in sol.get("pasos", []))
        resp = c.get("responsable", {})
        resp_linea = (
            f"<strong>Responsable:</strong> {resp.get('actor', '-')} "
            f"({resp.get('frente', '-')}) &nbsp;·&nbsp; "
            f"<a href='mailto:{resp.get('correo', '')}' style='color:{BRAND_GREEN}'>{resp.get('correo', '-')}</a>"
            if resp else ""
        )
        bloques.append(
            f"<div style='border:1px solid #e1e4e8;border-left:4px solid {BRAND_GREEN};border-radius:6px;padding:12px 14px;margin:10px 0'>"
            f"<div style='font-weight:600'>{c['categoria']} "
            f"<span style='color:#fff;background:{color};padding:1px 7px;border-radius:3px;font-size:11px'>{c['severidad']}</span> "
            f"<span style='color:#777;font-weight:400'>· {c['conteo']} casos</span></div>"
            f"<div style='font-size:12px;color:#555;margin:4px 0'>{resp_linea}</div>"
            f"<div style='font-size:12px;color:#555;margin:4px 0'>"
            f"<strong>Área solución:</strong> {sol.get('area_responsable', '-')} &nbsp;|&nbsp; "
            f"<strong>Sistemas:</strong> {sol.get('sistemas', '-')}</div>"
            f"<ol style='font-size:13px;margin:6px 0 0 18px;padding:0'>{pasos}</ol>"
            "</div>"
        )
    return (
        f"<h3 style='color:{BRAND_GREEN}'>Procedimiento de solución por causa raíz</h3>"
        "<p style='margin:4px 0;color:#555;font-size:13px'>Pasos definidos por el analista. "
        "Las categorías marcadas como pendientes aún no tienen procedimiento asignado.</p>"
        + "".join(bloques)
    )


def build_html(summary, narrativa_bloque=""):
    lote = summary["lote"]
    s3_url = f"https://{lote['bucket']}.s3.amazonaws.com/{lote['key']}"

    cat_rows = "".join(_row_categoria(c) for c in summary["categorias"])
    cli_rows = "".join(_row_cliente(c) for c in summary["top_clientes"])

    stock = summary.get("alerta_stock", {})
    stock_count = stock.get("conteo", 0)
    stock_docs = stock.get("documentos", [])
    stock_items = "".join(
        f"<li style='margin:2px 0'><code>{d['documento']}</code> — {d['mensaje']}</li>"
        for d in stock_docs[:20]
    )
    stock_section = (
        f"<h3 style='color:{BRAND_GREEN}'>Alerta diferenciada — Stock / ATP ({stock_count})</h3>"
        f"<p style='margin:4px 0;color:#555'>Errores de disponibilidad (no son fallas de migración de cliente). "
        f"Mostrando primeros {min(20, len(stock_docs))} de {stock_count}.</p>"
        f"<ul style='font-size:13px'>{stock_items or '<li>Sin casos en este lote.</li>'}</ul>"
    )

    th = f"background:{BRAND_GREEN};color:#fff"  # cabecera de tabla con la marca
    h3 = f"color:{BRAND_GREEN}"

    return f"""<html><body style="margin:0;padding:0;background:#f4f6f5">
    <div style="font-family:Segoe UI,Arial,sans-serif;color:#222;max-width:800px;margin:0 auto;background:#fff">

      <!-- Encabezado con la marca: titulo a la izquierda, logo a la derecha -->
      <table role="presentation" width="100%" style="background:{BRAND_GREEN};border-collapse:collapse">
        <tr>
          <td style="padding:20px 24px;vertical-align:middle">
            <h2 style="margin:0;color:#fff;font-size:20px">Alerta de errores — Integración AS/400 → SAP</h2>
            <p style="margin:6px 0 0;color:#d8f0e4;font-size:13px">Lote procesado: {lote['procesado_utc']}</p>
          </td>
          <td style="padding:12px 24px;vertical-align:middle;text-align:right;white-space:nowrap">
            <img src="cid:tailoy_logo" alt="Tai Loy" width="64" height="64"
                 style="display:inline-block;border-radius:8px;background:#fff" />
          </td>
        </tr>
      </table>
      <div style="height:4px;background:{BRAND_YELLOW}"></div>

      <div style="padding:20px 24px">
      <div style="background:#f4faf6;border:1px solid #d7ebe0;border-left:4px solid {BRAND_GREEN};border-radius:6px;padding:14px;margin:0 0 12px">
        <strong>Total de errores:</strong> {lote['total_errores']} &nbsp;|&nbsp;
        <strong>Clientes afectados:</strong> {lote['clientes_afectados']}<br>
        <strong>Archivo:</strong> <code>{lote['key']}</code>
      </div>

      {narrativa_bloque}

      <h3 style="{h3}">Resumen por categoría (causa raíz)</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px">
        <thead><tr style="{th}">
          <th style="padding:8px 10px;text-align:left">Categoría</th>
          <th style="padding:8px 10px;text-align:right">Conteo</th>
          <th style="padding:8px 10px;text-align:left">Severidad</th>
          <th style="padding:8px 10px;text-align:left">Equipo</th>
          <th style="padding:8px 10px;text-align:right">Clientes</th>
        </tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>

      {_runbooks_html(summary)}

      {stock_section}

      <h3 style="{h3}">Top clientes afectados</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px">
        <thead><tr style="{th}">
          <th style="padding:8px 10px;text-align:left">Cliente</th>
          <th style="padding:8px 10px;text-align:right">Docs</th>
          <th style="padding:8px 10px;text-align:left">Categorías</th>
        </tr></thead>
        <tbody>{cli_rows}</tbody>
      </table>

      <p style="margin-top:16px">
        <a href="{s3_url}" style="color:{BRAND_GREEN};font-weight:600">Ver archivo en S3</a>
      </p>
      </div>

      <div style="border-top:3px solid {BRAND_YELLOW};background:{BRAND_GREEN};padding:12px 24px">
        <p style="margin:0;color:#d8f0e4;font-size:12px">Generado automáticamente por el sistema de alertas de integración AS/400 → SAP.</p>
      </div>
    </div>
    </body></html>"""


def build_text(summary, narrativa=""):
    lote = summary["lote"]
    lines = [
        "Alerta de errores - Integracion AS/400 -> SAP",
        f"Lote: {lote['procesado_utc']}",
        f"Total errores: {lote['total_errores']} | Clientes afectados: {lote['clientes_afectados']}",
        f"Archivo: {lote['key']}",
    ]
    if narrativa:
        lines += ["", narrativa]
    lines += ["", "Resumen por categoria:"]
    for c in summary["categorias"]:
        lines.append(
            f"  - {c['categoria']}: {c['conteo']} [{c['severidad']}] "
            f"({c['equipo']}, {c['clientes_afectados']} clientes)"
        )
    lines += ["", "Procedimiento de solucion por causa raiz:"]
    for c in summary["categorias"]:
        sol = c.get("solucion", {})
        resp = c.get("responsable", {})
        lines.append(f"  * {c['categoria']}")
        lines.append(
            f"    responsable: {resp.get('actor', '-')} ({resp.get('frente', '-')}) "
            f"- {resp.get('correo', '-')}"
        )
        lines.append(f"    area solucion: {sol.get('area_responsable', '-')} | sistemas: {sol.get('sistemas', '-')}")
        for i, paso in enumerate(sol.get("pasos", []), 1):
            lines.append(f"      {i}. {paso}")
    stock = summary.get("alerta_stock", {})
    lines.append("")
    lines.append(f"Alerta Stock/ATP: {stock.get('conteo', 0)} documentos")
    lines.append("")
    lines.append("Top clientes:")
    for c in summary["top_clientes"]:
        lines.append(f"  - {c['cliente']}: {c['total']} docs")
    return "\n".join(lines)


def _enviar_correo(subject, html, text):
    """
    Envia el correo con el logo embebido (CID) via send_raw_email (MIME multipart).
    Si el logo no esta disponible, cae a send_email normal (sin logo) para no
    bloquear la alerta.
    """
    try:
        with open(LOGO_PATH, "rb") as fh:
            logo_bytes = fh.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Logo no disponible (%s); se envia sin logo embebido.", exc)
        return ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": RECIPIENTS},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            },
        )

    # multipart/related: cuerpo alternativo (texto+html) + imagen embebida
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = SES_SENDER
    msg["To"] = ", ".join(RECIPIENTS)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    img = MIMEImage(logo_bytes, _subtype="png")
    img.add_header("Content-ID", f"<{LOGO_CID}>")
    img.add_header("Content-Disposition", "inline", filename="tailoy-logo.png")
    msg.attach(img)

    return ses.send_raw_email(
        Source=SES_SENDER,
        Destinations=RECIPIENTS,
        RawMessage={"Data": msg.as_string()},
    )


def handler(event, context):
    logger.info("Evento SNS recibido.")
    if not SES_SENDER or not RECIPIENTS:
        raise RuntimeError("SES_SENDER y SES_RECIPIENT deben estar configurados.")

    for record in event.get("Records", []):
        raw = record["Sns"]["Message"]
        summary = json.loads(raw)

        # 1) narrativa (IA con fallback) — 2) ensamblado con cifras deterministas
        texto_narrativa, origen = narrativa_ia(summary)
        html = build_html(summary, _narrativa_html(texto_narrativa, origen))
        text = build_text(summary, texto_narrativa)

        total = summary["lote"]["total_errores"]
        subject = f"[AS400->SAP] {total} errores de integracion - {summary['lote']['key'].split('/')[-1]}"

        resp = _enviar_correo(subject, html, text)
        logger.info("Correo enviado (narrativa=%s). MessageId=%s", origen, resp.get("MessageId"))

    return {"statusCode": 200}
