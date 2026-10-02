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
  SES_RECIPIENT   destinatario (obligatorio)
  MODEL_ID        inference profile Bedrock (default us.anthropic.claude-sonnet-5-5)
  BEDROCK_MAX_TOKENS  tope de tokens de salida (default 350)
  AWS_REGION      región (la inyecta Lambda automáticamente)
"""

import json
import os
import logging

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
SES_RECIPIENT = os.environ.get("SES_RECIPIENT", "")
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-5-5")
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "350"))

SEVERIDAD_COLOR = {
    "CRITICA": "#c0392b",
    "WARNING": "#e67e22",
    "INFO": "#2980b9",
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
    """Construye el prompt de usuario con las cifras ya calculadas."""
    lote = summary["lote"]
    cats = "; ".join(
        f"{c['categoria']}={c['conteo']} ({c['severidad']}, equipo {c['equipo']})"
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
        "2) PRÓXIMA ACCIÓN: una viñeta por equipo responsable con la acción concreta.\n"
        "No inventes cifras. No incluyas tablas. Máximo 180 palabras."
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
        "<div style='background:#eef5fb;border-left:4px solid #2980b9;"
        "padding:12px 14px;margin:12px 0;border-radius:4px'>"
        f"<div style='font-size:14px;line-height:1.5'>{cuerpo}</div>"
        f"<div style='color:#999;font-size:11px;margin-top:8px'>{etiqueta}</div>"
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
        f"<h3 style='color:#2980b9'>Alerta diferenciada — Stock / ATP ({stock_count})</h3>"
        f"<p style='margin:4px 0;color:#555'>Errores de disponibilidad (no son fallas de migración de cliente). "
        f"Mostrando primeros {min(20, len(stock_docs))} de {stock_count}.</p>"
        f"<ul style='font-size:13px'>{stock_items or '<li>Sin casos en este lote.</li>'}</ul>"
    )

    return f"""<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#222;max-width:800px">
      <h2 style="margin-bottom:0">Alerta de errores — Integración AS/400 → SAP</h2>
      <p style="color:#777;margin-top:4px">Lote procesado: {lote['procesado_utc']}</p>

      <div style="background:#f8f9fa;border:1px solid #e1e4e8;border-radius:6px;padding:14px;margin:12px 0">
        <strong>Total de errores:</strong> {lote['total_errores']} &nbsp;|&nbsp;
        <strong>Clientes afectados:</strong> {lote['clientes_afectados']}<br>
        <strong>Archivo:</strong> <code>{lote['key']}</code>
      </div>

      {narrativa_bloque}

      <h3>Resumen por categoría (causa raíz)</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px">
        <thead><tr style="background:#2c3e50;color:#fff">
          <th style="padding:8px 10px;text-align:left">Categoría</th>
          <th style="padding:8px 10px;text-align:right">Conteo</th>
          <th style="padding:8px 10px;text-align:left">Severidad</th>
          <th style="padding:8px 10px;text-align:left">Equipo</th>
          <th style="padding:8px 10px;text-align:right">Clientes</th>
        </tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>

      {stock_section}

      <h3>Top clientes afectados</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px">
        <thead><tr style="background:#2c3e50;color:#fff">
          <th style="padding:8px 10px;text-align:left">Cliente</th>
          <th style="padding:8px 10px;text-align:right">Docs</th>
          <th style="padding:8px 10px;text-align:left">Categorías</th>
        </tr></thead>
        <tbody>{cli_rows}</tbody>
      </table>

      <p style="margin-top:16px">
        <a href="{s3_url}" style="color:#2980b9">Ver archivo en S3</a>
      </p>
      <hr style="border:none;border-top:1px solid #eee">
      <p style="color:#999;font-size:12px">Generado automáticamente por el sistema de alertas de integración AS/400 → SAP.</p>
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
    stock = summary.get("alerta_stock", {})
    lines.append("")
    lines.append(f"Alerta Stock/ATP: {stock.get('conteo', 0)} documentos")
    lines.append("")
    lines.append("Top clientes:")
    for c in summary["top_clientes"]:
        lines.append(f"  - {c['cliente']}: {c['total']} docs")
    return "\n".join(lines)


def handler(event, context):
    logger.info("Evento SNS recibido.")
    if not SES_SENDER or not SES_RECIPIENT:
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

        resp = ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": [SES_RECIPIENT]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Correo enviado (narrativa=%s). MessageId=%s", origen, resp.get("MessageId"))

    return {"statusCode": 200}
