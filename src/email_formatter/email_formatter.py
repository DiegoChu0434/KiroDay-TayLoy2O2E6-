"""
Lambda formateadora de correo (integración AS/400 -> SAP).

Se suscribe al topic SNS que publica la Lambda analizadora. Toma el resumen
del lote (JSON) y compone UN único correo HTML estructurado, que envía por SES
a la bandeja destino.

Secciones del correo (ver especificaciones §4.5):
  1. Encabezado: fecha del lote, total de errores, nº de clientes afectados.
  2. Resumen por categoría (causa raíz, conteo, severidad, equipo).
  3. Alerta diferenciada de STOCK/ATP.
  4. Top clientes afectados.
  5. Enlace al CSV en S3.

Variables de entorno:
  SES_SENDER      remitente verificado en SES (obligatorio)
  SES_RECIPIENT   destinatario (bandeja personal) (obligatorio)
  AWS_REGION      región (la inyecta Lambda automáticamente)
"""

import json
import os
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client("ses")

SES_SENDER = os.environ.get("SES_SENDER", "")
SES_RECIPIENT = os.environ.get("SES_RECIPIENT", "")

SEVERIDAD_COLOR = {
    "CRITICA": "#c0392b",
    "WARNING": "#e67e22",
    "INFO": "#2980b9",
}


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


def build_html(summary):
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


def build_text(summary):
    lote = summary["lote"]
    lines = [
        "Alerta de errores - Integracion AS/400 -> SAP",
        f"Lote: {lote['procesado_utc']}",
        f"Total errores: {lote['total_errores']} | Clientes afectados: {lote['clientes_afectados']}",
        f"Archivo: {lote['key']}",
        "",
        "Resumen por categoria:",
    ]
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

        html = build_html(summary)
        text = build_text(summary)
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
        logger.info("Correo enviado. MessageId=%s", resp.get("MessageId"))

    return {"statusCode": 200}
