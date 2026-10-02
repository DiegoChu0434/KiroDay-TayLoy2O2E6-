"""
Lambda analizadora de errores HA00 (integración AS/400 -> SAP).

Flujo:
  1. Se dispara por un evento ObjectCreated de S3 (nuevo CSV de errores).
  2. Descarga y parsea el CSV (delimitado por '|', campos con padding).
  3. Clasifica cada error por causa raíz (catálogo de negocio).
  4. Agrupa por cliente + categoría.
  5. Separa la alerta diferenciada de STOCK/ATP.
  6. Emite métricas custom a CloudWatch (una por categoría).
  7. Escribe un resumen estructurado (JSON) en el log y lo publica en SNS,
     para que la Lambda formateadora componga un único correo por lote.

Variables de entorno esperadas:
  METRIC_NAMESPACE   namespace de CloudWatch (default TaiLoy/IntegracionAS400SAP)
  SNS_TOPIC_ARN      ARN del topic SNS de alertas (opcional; si no, solo métricas+log)
"""

import csv
import io
import json
import os
import re
import logging
from collections import defaultdict
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
cloudwatch = boto3.client("cloudwatch")
sns = boto3.client("sns")

METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "TaiLoy/IntegracionAS400SAP")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

# Índices de columnas de la tabla HA00 (ver especificaciones §2.2)
COL_ORIGEN = 0      # H0CIN
COL_CORRELATIVO = 1  # H0COR
COL_DOCUMENTO = 3   # H0TR1
COL_MENSAJE = 4     # H0TR2  (texto del error devuelto por SAP)
COL_DOC_SAP = 5     # H0SAP  (vacío = no se creó)
COL_FECHA = 7       # H0FCR

# ---------------------------------------------------------------------------
# Catálogo de clasificación de errores por causa raíz.
# Cada entrada: (codigo, severidad, regex, equipo_responsable)
# El orden importa: se evalúa de arriba hacia abajo, primera coincidencia gana.
# ---------------------------------------------------------------------------
ERROR_RULES = [
    (
        "PARTNER_FUNCTIONS_FALTANTES",
        "CRITICA",
        re.compile(r"determinar el (pagador|receptor|solicitante|destinatario)", re.IGNORECASE),
        "Datos Maestros",
    ),
    (
        "DATOS_CLIENTE_INCOMPLETOS",
        "CRITICA",
        re.compile(r"Valor de Cliente es obligatorio", re.IGNORECASE),
        "Datos Maestros / Integracion",
    ),
    (
        "CLIENTE_SIN_MAESTRO_VENTAS_KNVV",
        "WARNING",
        re.compile(r"Falta tabla maestra de clientes KNVV", re.IGNORECASE),
        "Datos Maestros",
    ),
    (
        "DEUDOR_INEXISTENTE",
        "WARNING",
        re.compile(r"El deudor .* no existe", re.IGNORECASE),
        "Datos Maestros",
    ),
    (
        "STOCK_INSUFICIENTE_ATP",
        "INFO",
        re.compile(r"util\.?\s*libre por debajo", re.IGNORECASE),
        "Operaciones",
    ),
    (
        "MATERIAL_BLOQUEADO",
        "INFO",
        re.compile(r"estan bloqueados por el usuario", re.IGNORECASE),
        "Transitorio",
    ),
    (
        "CUENTA_MAYOR_INEXISTENTE",
        "WARNING",
        re.compile(r"cta\.?\s*mayor .* no existe", re.IGNORECASE),
        "Contabilidad",
    ),
]

STOCK_CATEGORY = "STOCK_INSUFICIENTE_ATP"

# ---------------------------------------------------------------------------
# Catálogo de RUNBOOKS de solución por causa raíz (definido por el analista).
# Es determinista: la IA puede referenciarlo pero NO lo inventa.
# Cada entrada: pasos (procedimiento), sistemas involucrados, área responsable.
# Las categorías sin procedimiento del analista quedan como "pendiente".
# ---------------------------------------------------------------------------
RUNBOOKS = {
    "PARTNER_FUNCTIONS_FALTANTES": {
        "pasos": [
            "Se crea una venta para el canal e-commerce (RAPPI / PedidosYa) que se atiende en la tienda.",
            "Al subir la venta a SAP para contabilizar, el cliente (BP) no tiene asignada el área de ventas del canal e-commerce.",
            "Ampliar en SAP a este cliente al canal E-COMMERCE (u otro canal no ampliado).",
            "Volver a pasar la venta: se llega a contabilizar.",
        ],
        "sistemas": "AS400 / e-commerce (RAPPI, PedidosYa) / SAP (BP, área de ventas)",
        "area_responsable": "Datos Maestros",
    },
    "DATOS_CLIENTE_INCOMPLETOS": {
        "pasos": [
            "Al crear un cliente en SAP debe tener el VENDEDOR asignado.",
            "Modificar el cliente en SAP y asignar un vendedor.",
            "Volver a enviar el cliente.",
        ],
        "sistemas": "SAP (maestro de cliente)",
        "area_responsable": "Datos Maestros / Comercial",
    },
    "STOCK_INSUFICIENTE_ATP": {
        "pasos": [
            "Se envía una venta facturada de una tienda; físicamente el cliente ya se llevó el producto (había stock en tienda).",
            "Al contabilizar en SAP no hay stock: la tienda recibió la mercadería pero no aplicó el ingreso a su almacén.",
            "Ingresar la mercadería en la tienda y enviar ese movimiento de ingreso a SAP.",
            "Una vez ingresado y contabilizado en SAP, se puede contabilizar la venta pendiente.",
        ],
        "sistemas": "Tienda (ingreso de mercadería) / SAP (stock, ATP)",
        "area_responsable": "Operaciones / Logística tienda",
    },
    "DEUDOR_INEXISTENTE": {
        "pasos": [
            "Al asignar una línea de crédito en tienda, el cliente se convierte en deudor.",
            "Una venta al crédito (sistema NO SAP) no contabiliza porque el BP no tiene ampliado el ROL DEUDOR.",
            "Ingresar a SAP el BP y asignar el ROL DEUDOR.",
            "Enviar la venta al crédito: pasa a contabilizarse.",
        ],
        "sistemas": "Tienda (crédito) / SAP (BP, rol deudor)",
        "area_responsable": "Datos Maestros / Créditos",
    },
    # --- Pendientes de procedimiento del analista (acción genérica por ahora) ---
    "CLIENTE_SIN_MAESTRO_VENTAS_KNVV": {
        "pasos": ["Pendiente de procedimiento del analista. Escalar a Datos Maestros para completar la vista de área de ventas (KNVV) del cliente."],
        "sistemas": "SAP (maestro de ventas KNVV)",
        "area_responsable": "Datos Maestros",
    },
    "MATERIAL_BLOQUEADO": {
        "pasos": ["Pendiente de procedimiento del analista. Error transitorio: reintentar cuando el material deje de estar bloqueado por el usuario."],
        "sistemas": "SAP (datos de centro del material)",
        "area_responsable": "Datos Maestros / Operaciones",
    },
    "CUENTA_MAYOR_INEXISTENTE": {
        "pasos": ["Pendiente de procedimiento del analista. Escalar a Contabilidad para crear/validar la cuenta de mayor."],
        "sistemas": "SAP (plan de cuentas)",
        "area_responsable": "Contabilidad",
    },
    "OTRO": {
        "pasos": ["Sin categorizar. Requiere revisión manual y definición de procedimiento."],
        "sistemas": "Por determinar",
        "area_responsable": "Revisión manual",
    },
}


def runbook(categoria):
    """Devuelve el runbook de solución para una categoría (o uno vacío por defecto)."""
    return RUNBOOKS.get(
        categoria,
        {"pasos": ["Sin procedimiento definido."], "sistemas": "Por determinar", "area_responsable": "Revisión manual"},
    )


def classify(message: str):
    """Devuelve (codigo, severidad, equipo) para un mensaje de error."""
    msg = (message or "").strip()
    for codigo, severidad, regex, equipo in ERROR_RULES:
        if regex.search(msg):
            return codigo, severidad, equipo
    return "OTRO", "WARNING", "Revision manual"


def extract_cliente(documento: str, mensaje: str) -> str:
    """
    Intenta identificar el cliente afectado.
    Primero busca un nº de cliente en el mensaje (p.ej. 'Cliente 1000172706:'),
    si no, usa el número de documento como clave de agrupación.
    """
    m = re.search(r"Cliente\s+(\d+)", mensaje or "", re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"deudor\s+(\S+)", mensaje or "", re.IGNORECASE)
    if m:
        return m.group(1)
    # fallback: parte del documento (sin el correlativo tras el guión)
    doc = (documento or "").strip()
    if "-" in doc:
        return doc.split("-")[0]
    return doc or "DESCONOCIDO"


def parse_csv(body: str):
    """Parsea el CSV HA00 y devuelve lista de dicts normalizados."""
    reader = csv.reader(io.StringIO(body), delimiter="|")
    rows = list(reader)
    if not rows:
        return []
    data = rows[1:]  # saltar header
    registros = []
    for cols in data:
        if len(cols) <= COL_MENSAJE:
            continue
        mensaje = cols[COL_MENSAJE].strip()
        documento = cols[COL_DOCUMENTO].strip() if len(cols) > COL_DOCUMENTO else ""
        codigo, severidad, equipo = classify(mensaje)
        registros.append(
            {
                "documento": documento,
                "mensaje": mensaje,
                "categoria": codigo,
                "severidad": severidad,
                "equipo": equipo,
                "cliente": extract_cliente(documento, mensaje),
                "fecha": cols[COL_FECHA].strip() if len(cols) > COL_FECHA else "",
            }
        )
    return registros


def build_summary(registros, bucket, key):
    """Construye el resumen agregado del lote."""
    por_categoria = defaultdict(int)
    severidad_por_categoria = {}
    equipo_por_categoria = {}
    clientes_por_categoria = defaultdict(set)
    docs_stock = []

    for r in registros:
        cat = r["categoria"]
        por_categoria[cat] += 1
        severidad_por_categoria[cat] = r["severidad"]
        equipo_por_categoria[cat] = r["equipo"]
        clientes_por_categoria[cat].add(r["cliente"])
        if cat == STOCK_CATEGORY:
            docs_stock.append({"documento": r["documento"], "mensaje": r["mensaje"]})

    # top clientes por nº de documentos afectados
    docs_por_cliente = defaultdict(lambda: defaultdict(int))
    for r in registros:
        docs_por_cliente[r["cliente"]][r["categoria"]] += 1
    top_clientes = sorted(
        (
            {
                "cliente": cli,
                "total": sum(cats.values()),
                "categorias": dict(cats),
            }
            for cli, cats in docs_por_cliente.items()
        ),
        key=lambda x: x["total"],
        reverse=True,
    )[:15]

    categorias = []
    for cat, count in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True):
        rb = runbook(cat)
        categorias.append(
            {
                "categoria": cat,
                "conteo": count,
                "severidad": severidad_por_categoria.get(cat, "WARNING"),
                "equipo": equipo_por_categoria.get(cat, "Revision manual"),
                "clientes_afectados": len(clientes_por_categoria.get(cat, set())),
                "solucion": {
                    "pasos": rb["pasos"],
                    "sistemas": rb["sistemas"],
                    "area_responsable": rb["area_responsable"],
                },
            }
        )

    total = len(registros)
    clientes_totales = len({r["cliente"] for r in registros})

    return {
        "lote": {
            "bucket": bucket,
            "key": key,
            "procesado_utc": datetime.now(timezone.utc).isoformat(),
            "total_errores": total,
            "clientes_afectados": clientes_totales,
        },
        "categorias": categorias,
        "alerta_stock": {
            "categoria": STOCK_CATEGORY,
            "conteo": por_categoria.get(STOCK_CATEGORY, 0),
            "documentos": docs_stock[:50],
        },
        "top_clientes": top_clientes,
    }


def emit_metrics(summary):
    """Emite una métrica por categoría a CloudWatch."""
    metric_data = []
    for c in summary["categorias"]:
        metric_data.append(
            {
                "MetricName": "ErroresPorCategoria",
                "Dimensions": [
                    {"Name": "Categoria", "Value": c["categoria"]},
                    {"Name": "Severidad", "Value": c["severidad"]},
                ],
                "Value": c["conteo"],
                "Unit": "Count",
            }
        )
    metric_data.append(
        {
            "MetricName": "TotalErroresLote",
            "Value": summary["lote"]["total_errores"],
            "Unit": "Count",
        }
    )
    # CloudWatch acepta máx 1000 por llamada; aquí son pocas
    if metric_data:
        cloudwatch.put_metric_data(Namespace=METRIC_NAMESPACE, MetricData=metric_data)
    logger.info("Métricas emitidas: %d", len(metric_data))


def publish_sns(summary):
    """Publica el resumen en SNS para la Lambda formateadora."""
    if not SNS_TOPIC_ARN:
        logger.warning("SNS_TOPIC_ARN no configurado; se omite publicación.")
        return
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Alerta errores integracion AS400-SAP",
        Message=json.dumps(summary, ensure_ascii=False),
    )
    logger.info("Resumen publicado en SNS.")


def handler(event, context):
    logger.info("Evento recibido: %s", json.dumps(event)[:1000])
    procesados = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info("Procesando s3://%s/%s", bucket, key)

        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read().decode("latin-1")  # EBCDIC-export -> latin-1

        registros = parse_csv(body)
        summary = build_summary(registros, bucket, key)

        # log estructurado (sirve como respaldo para metric filters)
        logger.info("RESUMEN_LOTE %s", json.dumps(summary, ensure_ascii=False))

        emit_metrics(summary)
        publish_sns(summary)
        procesados.append({"key": key, "total": summary["lote"]["total_errores"]})

    return {"statusCode": 200, "procesados": procesados}
