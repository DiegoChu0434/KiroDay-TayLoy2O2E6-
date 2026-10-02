# Recursos creados manualmente por CLI (fuera de CloudFormation)

> Registro de todo lo que se crea a mano para pruebas, para poder borrarlo luego.
> Cuenta: `971431176203` · Región: `us-east-1` · Profile: `tailoydev`

## Contexto

El bucket de producción `tailoy-poc-s3-bucket-raw` **NO se toca**. Ya tiene una
notificación `ObjectCreated` activa que invoca la Lambda `tai-loy-poc-crawl-tables`
sobre el prefijo `tai-loy/maestro/equivalencia/*.csv`. Sobrescribir su configuración
de notificaciones rompería ese pipeline existente.

Para probar el disparo automático (Fase C) se crea un **bucket aislado** que replica
el patrón de llegada real:

- Ruta real: `tai-loy/maestro/raw/ASPRD.ha00/`
- Patrón de nombre: `ha00_YYYYMMDD.csv` (un archivo nuevo por día, vía `PutObject`)
- Evento que dispara: `s3:ObjectCreated:*`

## Recursos creados

| # | Recurso | Identificador | Creado | Propósito |
|---|---------|---------------|--------|-----------|
| 1 | S3 bucket (prueba) | `ha00-alertas-test-ingest-971431176203` | Fase C | Bucket aislado que imita el patrón de llegada de los CSV HA00 |
| 2 | S3 notification | config `ObjectCreated:*` prefijo `tai-loy/maestro/raw/ASPRD.ha00/` sufijo `.csv` → Lambda `ha00-alertas-analyzer` | Fase C | Disparo automático del análisis |
| 3 | Lambda permission | `AllowTestBucketInvoke` en `ha00-alertas-analyzer` | Fase C | Permite que el bucket de prueba invoque la Lambda |
| 4 | IAM inline policy | `read-test-bucket` en rol `ha00-alertas-analyzer-role` | Fase C | Permite a la analizadora leer objetos del bucket de prueba |
| 5 | S3 bucket (curated) | `ha00-alertas-curated-971431176203` | Fase Power BI | Datos curados para Athena/Power BI + resultados de Athena |
| 6 | Glue database | `tailoy_ha00_alertas` | Fase Power BI | Base de datos aislada (NO reutiliza `tailoy_sap_as400`) |
| 7 | Glue table | `tailoy_ha00_alertas.errores_detalle` | Fase Power BI | Hechos: 1 fila por error (Parquet, partition projection por `fecha_lote`) |
| 8 | Glue table | `tailoy_ha00_alertas.alertas_enviadas` | Fase Power BI | Dimensión de lote: 1 fila por lote (JSON) |
| 9 | Athena workgroup | `ha00-powerbi` | Fase Power BI | Workgroup de consultas para Power BI |
| 10 | SES identity (prueba) | `dchavez@bigcheese.com.uy` | Pruebas | Destinatario adicional para pruebas de correo (verificación manual) |
| 11 | SES identity | `madelgado@tailoy.com.pe` | Destinatario | Destinatario del flujo de alertas (verificación manual pendiente) |
| 11b | SES identity | `dchu@tailoy.com.pe` | Destinatario | Destinatario del flujo de alertas (verificación manual pendiente) |

> `diego9313dg@gmail.com` fue eliminada de SES (era solo para diagnóstico de entrega).
| 12 | SES configuration set | `ha00-diagnostico` (event destination `a-sqs`) | Diagnóstico entrega | Publica eventos Send/Delivery/Bounce/Reject/Delay de los correos que lo usen |
| 13 | SNS topic | `ha00-ses-eventos` | Diagnóstico entrega | Recibe los eventos del configuration set |
| 14 | SQS queue + suscripción | `ha00-ses-eventos` (suscrita al topic, raw delivery) | Diagnóstico entrega | Permite leer los eventos de entrega por CLI |

## Tabla a conectar en Power BI

- **Tabla de hechos principal:** `tailoy_ha00_alertas.errores_detalle`
- **Dimensión de lote:** `tailoy_ha00_alertas.alertas_enviadas` (se relaciona por `lote_id`)
- **Workgroup Athena:** `ha00-powerbi` · región `us-east-1`
- Datos de ejemplo cargados: partición `fecha_lote=2026-09-30` (2.474 filas del dataset de ejemplo).

## Cómo borrar todo

```bash
export AWS_PROFILE=tailoydev AWS_DEFAULT_REGION=us-east-1
B=ha00-alertas-test-ingest-971431176203

# 1. Vaciar y borrar el bucket de prueba
aws s3 rm "s3://$B" --recursive
aws s3api delete-bucket --bucket "$B"

# 2. Quitar el permiso de invocación agregado a la Lambda del stack
aws lambda remove-permission --function-name ha00-alertas-analyzer --statement-id AllowTestBucketInvoke

# 2b. Quitar la policy de lectura del bucket de prueba del rol de la analizadora
aws iam delete-role-policy --role-name ha00-alertas-analyzer-role --policy-name read-test-bucket

# 3. Borrar recursos de la fase Power BI (Athena / Glue / bucket curated)
aws athena delete-work-group --work-group ha00-powerbi --recursive-delete-option
aws glue delete-table --database-name tailoy_ha00_alertas --name errores_detalle
aws glue delete-table --database-name tailoy_ha00_alertas --name alertas_enviadas
aws glue delete-database --name tailoy_ha00_alertas
CB=ha00-alertas-curated-971431176203
aws s3 rm "s3://$CB" --recursive
aws s3api delete-bucket --bucket "$CB"

# 4. Borrar las identidades SES de prueba creadas por CLI
aws sesv2 delete-email-identity --email-identity dchavez@bigcheese.com.uy
aws sesv2 delete-email-identity --email-identity madelgado@tailoy.com.pe
aws sesv2 delete-email-identity --email-identity dchu@tailoy.com.pe

# 4b. Borrar el diagnóstico de entrega SES (configuration set + SNS + SQS)
aws sesv2 delete-configuration-set --configuration-set-name ha00-diagnostico
aws sns delete-topic --topic-arn arn:aws:sns:us-east-1:971431176203:ha00-ses-eventos
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name ha00-ses-eventos --query QueueUrl --output text)"

# 5. (El stack CloudFormation se borra aparte)
# aws cloudformation delete-stack --stack-name ha00-alertas
```

> Nota: la notificación vive dentro del bucket de prueba, así que se elimina al
> borrar el bucket (paso 1). No hay nada que limpiar en el bucket de producción.
