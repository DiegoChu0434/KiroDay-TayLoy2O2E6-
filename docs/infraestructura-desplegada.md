# Infraestructura desplegada — Sistema de Alertas HA00 (AS/400 → SAP)

> Documento de referencia de **todo lo desplegado** en AWS para esta solución:
> lo que crea CloudFormation y lo que se creó manualmente por CLI.
>
> - **Cuenta:** `971431176203`
> - **Región:** `us-east-1`
> - **Profile:** `tailoydev` (SSO, rol `AWSAdministratorAccess`)
> - **Estado verificado:** 2026-10-02
> - **Stack CloudFormation:** `ha00-alertas` (`CREATE_COMPLETE`, creado 2026-10-02 17:24 UTC)

---

## 1. Vista general

El sistema tiene dos planos:

1. **Flujo de alertas (automático, productivo-POC):** un CSV nuevo de errores HA00
   aterriza en S3 → se analiza → se publica en SNS → una Lambda sintetiza un correo
   con IA (Bedrock) → se envía por SES. Desplegado por **CloudFormation** + el disparo
   S3 conectado por **CLI** sobre un bucket de prueba aislado.
2. **Analítica para Power BI (semi-manual):** el detalle clasificado del lote vive en
   S3 (Parquet), catalogado en Glue y consultable por Athena. Creado por **CLI**.

```
S3 (CSV ha00_YYYYMMDD.csv)
   │ ObjectCreated  [CLI: bucket de prueba]
   ▼
Lambda analizadora  ha00-alertas-analyzer        [CFN]
   │ publica resumen JSON
   ▼
SNS  ha00-alertas-alertas                        [CFN]
   │ invoca
   ▼
Lambda sintetizadora  ha00-alertas-email         [CFN]
   │ Bedrock (Claude Sonnet 5.5, inference profile) + fallback
   ▼
SES  →  correo HTML                              [CFN]

(aparte / analítica)
S3 curated (Parquet)  →  Glue  tailoy_ha00_alertas  →  Athena ha00-powerbi  →  Power BI   [CLI]
```

---

## 2. Desplegado por CloudFormation (stack `ha00-alertas`)

Plantilla: `infra/cloudformation.yaml`.
Despliegue: `./scripts/deploy.ps1` o `aws cloudformation deploy`.

| Logical ID | Tipo | Nombre físico |
|------------|------|---------------|
| AnalyzerFunction | `AWS::Lambda::Function` | `ha00-alertas-analyzer` |
| EmailFunction | `AWS::Lambda::Function` | `ha00-alertas-email` |
| AnalyzerRole | `AWS::IAM::Role` | `ha00-alertas-analyzer-role` |
| EmailFormatterRole | `AWS::IAM::Role` | `ha00-alertas-email-role` |
| AlertTopic | `AWS::SNS::Topic` | `ha00-alertas-alertas` |
| EmailSubscription | `AWS::SNS::Subscription` | (SNS → EmailFunction) |
| EmailInvokePermission | `AWS::Lambda::Permission` | permite a SNS invocar la sintetizadora |
| S3InvokePermission | `AWS::Lambda::Permission` | permite a S3 (bucket prod) invocar la analizadora |
| SesSenderIdentity | `AWS::SES::EmailIdentity` | `asilvera@tailoy.com.pe` |
| SesRecipientIdentity | `AWS::SES::EmailIdentity` | `asilvera+alertas@tailoy.com.pe` |
| CriticalAlarm | `AWS::CloudWatch::Alarm` | `ha00-alertas-errores-criticos` |

### Configuración de las Lambdas

| Función | Runtime | Memoria | Timeout | Notas |
|---------|---------|--------:|--------:|-------|
| `ha00-alertas-analyzer` | python3.12 | 256 MB | 120 s | ⚠️ Insuficiente para el archivo real de 339 MB (ver §5) |
| `ha00-alertas-email` | python3.12 | 256 MB | 30 s | Invoca Bedrock (`BEDROCK_MAX_TOKENS=2000`); cliente con timeouts 3s/12s |

### Parámetros usados en el despliegue

| Parámetro | Valor |
|-----------|-------|
| `SesSender` | `asilvera@tailoy.com.pe` |
| `SesRecipient` | `asilvera+alertas@tailoy.com.pe` |
| `RawBucketName` | `tailoy-poc-s3-bucket-raw` |
| `ErrorPrefix` | `tai-loy/maestro/raw/ASPRD.ha00/` |
| `ModelId` | `us.anthropic.claude-sonnet-5-5` (inference profile) |
| `BedrockMaxTokens` | `2000` (parámetro del stack; rango 500–8192) |

> **Nota de despliegue:** la plantilla declara remitente y destinatario como dos
> identidades SES separadas. Si se pasa **el mismo correo** a ambos parámetros, el
> despliegue falla en `AWS::EarlyValidation::ResourceExistenceCheck` (colisión de dos
> `EmailIdentity` iguales). Por eso el destinatario usa la subdirección `+alertas`,
> que llega a la misma bandeja de `asilvera@tailoy.com.pe`.

### Outputs del stack

| Output | Valor |
|--------|-------|
| `AnalyzerFunctionArn` | `arn:aws:lambda:us-east-1:971431176203:function:ha00-alertas-analyzer` |
| `EmailFunctionArn` | `arn:aws:lambda:us-east-1:971431176203:function:ha00-alertas-email` |
| `AlertTopicArn` | `arn:aws:sns:us-east-1:971431176203:ha00-alertas-alertas` |

### Borrar el stack

```bash
aws cloudformation delete-stack --stack-name ha00-alertas \
  --profile tailoydev --region us-east-1
```

---

## 3. Desplegado por CLI (fuera de CloudFormation)

> Detalle operativo y comandos de borrado en `infra/recursos-creados-manualmente.md`.

### 3.1 Disparo automático (Fase C) — bucket de prueba AISLADO

El bucket de producción **NO se toca** (ver §6). Para probar el flujo automático se
creó un bucket propio que replica el patrón de llegada real.

| Recurso | Identificador |
|---------|---------------|
| S3 bucket de ingesta (prueba) | `ha00-alertas-test-ingest-971431176203` |
| Notificación S3 | `ObjectCreated:*`, prefijo `tai-loy/maestro/raw/ASPRD.ha00/`, sufijo `.csv` → `ha00-alertas-analyzer` |
| Lambda permission | `AllowTestBucketInvoke` en `ha00-alertas-analyzer` |
| IAM inline policy | `read-test-bucket` en `ha00-alertas-analyzer-role` (lectura del bucket de prueba) |

Patrón de llegada validado: un `PutObject` de `ha00_YYYYMMDD.csv` por día dispara
`ObjectCreated` → invoca la analizadora sin intervención humana.

### 3.2 Analítica para Power BI (fase Power BI)

| Recurso | Identificador |
|---------|---------------|
| S3 bucket (curated) | `ha00-alertas-curated-971431176203` (SSE-S3, acceso público bloqueado) |
| Glue database | `tailoy_ha00_alertas` |
| Glue table (hechos) | `tailoy_ha00_alertas.errores_detalle` — Parquet, 1 fila por error, partition projection por `fecha_lote` |
| Glue table (lote) | `tailoy_ha00_alertas.alertas_enviadas` — JSON, 1 fila por lote |
| Athena workgroup | `ha00-powerbi` — resultados en `s3://ha00-alertas-curated-971431176203/athena-results/` |

**Datos cargados:** partición `fecha_lote=2026-09-30` con **2.474 filas** (dataset de
ejemplo `ha00_20260930.csv`, procesado con el mismo clasificador `analyzer.py` que el
correo). Carga **manual** por única vez (ver §5).

---

## 4. Conexión de Power BI

- **Conector:** Amazon Athena (driver ODBC de Athena, Power BI Desktop en Windows).
- **Región:** `us-east-1` · **Workgroup:** `ha00-powerbi`.
- **Base:** `tailoy_ha00_alertas`.
- **Tabla de hechos principal:** `tailoy_ha00_alertas.errores_detalle`.
- **Dimensión de lote:** `tailoy_ha00_alertas.alertas_enviadas` (relación por `lote_id`).
- Para refresco en Power BI **Service**: instalar el on-premises data gateway.

Consulta de validación (ejecutada OK en Athena, solo lectura):

```sql
SELECT categoria, severidad, count(*) AS n
FROM tailoy_ha00_alertas.errores_detalle
WHERE fecha_lote = '2026-09-30'
GROUP BY categoria, severidad
ORDER BY n DESC;
-- 1480 PARTNER_FUNCTIONS_FALTANTES, 404 DATOS_CLIENTE_INCOMPLETOS, 337 STOCK..., etc.
```

---

## 5. Estado y pendientes (importante)

| Tema | Estado |
|------|--------|
| Flujo de alertas por correo | ✅ Automático y probado end-to-end (S3→analizadora→SNS→sintetizadora→Bedrock→SES) |
| Narrativa IA (Bedrock) | ✅ `BEDROCK_MAX_TOKENS=2000` (código, plantilla y Lambda viva). Con 350 salía vacía por el reasoning de Sonnet 5.5 |
| Entrega de correo con remitente `@tailoy.com.pe` | ❌ Rechazado por DMARC `p=reject`. Requiere verificar el dominio en SES con Easy DKIM (admin DNS de Tai Loy). Ver §5.1 |
| Identidades SES | ✅ Ambas verificadas (`Success`) |
| SES | ⚠️ En **sandbox** (200 envíos/día). Solo envía a destinatarios verificados |
| Tabla `errores_detalle` | ✅ Con datos consultables, pero carga **MANUAL** por única vez |
| Escritura automática a la tabla | ❌ La analizadora **aún no escribe** en `errores_detalle`. Pendiente de código |
| `alertas_enviadas` | ⚠️ Tabla creada pero **vacía** (la sintetizadora aún no escribe su registro) |
| Memoria de la analizadora | ❌ 256 MB vs archivo real de **339 MB**. Falta subir memoria + lectura por streaming |
| Conexión al bucket de producción | ❌ No conectado (decisión deliberada; ver §6) |

> **Clave:** el correo y la tabla `errores_detalle` **comparten origen y clasificador**
> (por eso los números coinciden), pero hoy son **dos cargas independientes**: el correo
> es automático; la tabla se cargó a mano una vez. Para que la tabla se alimente sola en
> cada lote, falta que la Lambda analizadora escriba el Parquet tras publicar en SNS.

---

## 5.1 Entrega de correo: diagnóstico (2026-10-02)

Se creó un configuration set `ha00-diagnostico` que publica los eventos de SES en el
SNS `ha00-ses-eventos` → SQS `ha00-ses-eventos`, para ver la respuesta real del
servidor receptor. Resultado:

| Remitente | Destino | Resultado |
|-----------|---------|-----------|
| `asilvera@tailoy.com.pe` | Gmail / bigcheese (Google) | **Rechazado**: `550 5.7.26 Unauthenticated email from tailoy.com.pe is not accepted due to domain's DMARC policy` |
| `asilvera@tailoy.com.pe` | `asilvera+alertas@tailoy.com.pe` | Aceptado por FortiMail (`250 ... accepted for delivery`), pero no llega a la bandeja |
| `dchavez@bigcheese.com.uy` | Gmail y bigcheese | **Entregado** (`250 2.0.0 OK ... gsmtp`) |

Causa: `tailoy.com.pe` publica DMARC `p=reject; adkim=s; aspf=s`. SES envía firmando con
DKIM de `amazonses.com` y MAIL FROM de `amazonses.com`, que no se alinean con
`tailoy.com.pe`. El DMARC falla y el receptor rechaza o descarta. Las estadísticas
agregadas de SES (`get-send-statistics`) mostraban 0 rebotes; el rechazo solo se ve
con eventos.

Solución definitiva (requiere al administrador DNS de Tai Loy): verificar el dominio
`tailoy.com.pe` (o un subdominio, p. ej. `alertas.tailoy.com.pe`) en SES con Easy DKIM
y publicar los 3 CNAME. Con `adkim=s`, el remitente debe pertenecer exactamente al
dominio firmado.

Otro hallazgo (RESUELTO): con `BEDROCK_MAX_TOKENS=350`, Sonnet 5.5 gastaba todo el
presupuesto en razonamiento (`stopReason=max_tokens`, solo bloque `reasoningContent`),
la narrativa salía vacía y caía al fallback. Se subió a **2000** en el código
(`src/email_formatter/email_formatter.py`), en la plantilla
(`infra/cloudformation.yaml`) y en la env var de la Lambda ya desplegada
(`ha00-alertas-email`). Con 2000 responde completa (`end_turn`, ~850 tokens, ~6 s).

---

## 6. Lo que NO se tocó (recursos preexistentes)

- **Bucket de producción `tailoy-poc-s3-bucket-raw`:** no se modificó. Ya tenía una
  notificación `ObjectCreated` activa (prefijo `tai-loy/maestro/equivalencia/*.csv` →
  Lambda `tai-loy-poc-crawl-tables`). Por eso el disparo automático se probó en un
  bucket aislado y **no** con `put-bucket-notification-configuration` sobre el real
  (ese comando habría borrado la notificación existente).
- **Base/tabla `tailoy_sap_as400.logs_errores`:** no se reutilizó ni modificó. La
  analítica de esta solución usa su propia base `tailoy_ha00_alertas`.

---

## 7. Limpieza total

```bash
export AWS_PROFILE=tailoydev AWS_DEFAULT_REGION=us-east-1

# --- CLI: analítica Power BI ---
aws athena delete-work-group --work-group ha00-powerbi --recursive-delete-option
aws glue delete-table --database-name tailoy_ha00_alertas --name errores_detalle
aws glue delete-table --database-name tailoy_ha00_alertas --name alertas_enviadas
aws glue delete-database --name tailoy_ha00_alertas
aws s3 rm s3://ha00-alertas-curated-971431176203 --recursive
aws s3api delete-bucket --bucket ha00-alertas-curated-971431176203

# --- CLI: disparo automático (bucket de prueba) ---
aws s3 rm s3://ha00-alertas-test-ingest-971431176203 --recursive
aws s3api delete-bucket --bucket ha00-alertas-test-ingest-971431176203
aws lambda remove-permission --function-name ha00-alertas-analyzer --statement-id AllowTestBucketInvoke
aws iam delete-role-policy --role-name ha00-alertas-analyzer-role --policy-name read-test-bucket

# --- CLI: identidades SES de prueba y diagnóstico de entrega ---
aws sesv2 delete-email-identity --email-identity dchavez@bigcheese.com.uy
aws sesv2 delete-email-identity --email-identity diego9313dg@gmail.com
aws sesv2 delete-configuration-set --configuration-set-name ha00-diagnostico
aws sns delete-topic --topic-arn arn:aws:sns:us-east-1:971431176203:ha00-ses-eventos
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name ha00-ses-eventos --query QueueUrl --output text)"

# --- CloudFormation ---
aws cloudformation delete-stack --stack-name ha00-alertas
```

> SES: borrar las identidades es parte del stack. Si quedaran huérfanas:
> `aws sesv2 delete-email-identity --email-identity <correo>`.
