# Especificaciones — Sistema de Alertas para Errores de Integración AS/400 → SAP

> **Proyecto:** Monitoreo y alertamiento automatizado de errores en la migración/integración de clientes desde AS/400 hacia SAP
> **Repositorio destino:** https://github.com/DiegoChu0434/KiroDay-TayLoy2026.git
> **Fecha:** 2026-10-02
> **Estado:** Borrador v1 — Requerimientos y Diseño
> **Autor:** Equipo Data / Diego Chu (dchu@tailoy.com.pe)

---

## 1. Contexto de negocio

### 1.1 El problema

Tai Loy está migrando/integrando clientes y documentos de ventas desde el sistema legado **AS/400 (iSeries)** hacia **SAP**. Durante este flujo, SAP rechaza una cantidad significativa de documentos porque los datos del cliente llegan incompletos o no cumplen las reglas de negocio de SAP.

Hoy estos rechazos:

- Se registran en un log (tabla **HA00**) que se exporta a S3 como CSV diario.
- **No generan ninguna alerta** — alguien tiene que abrir el archivo manualmente para enterarse.
- **No se reprocesan automáticamente** — cada error espera corrección e intervención manual.
- Mezclan errores de **datos maestros** (migración) con errores **operativos de stock** (ATP), lo que infla la percepción de fallas de migración.

El resultado: errores que se detectan tarde, correcciones manuales lentas, y falta de visibilidad sobre la salud real de la integración.

### 1.2 El objetivo de negocio

1. **Detectar automáticamente** los errores apenas se generan.
2. **Clasificarlos por causa raíz** para saber qué equipo debe actuar (datos maestros vs. operaciones).
3. **Notificar de forma estructurada y accionable** a los responsables, sin ruido.
4. Sentar las bases para un **reproceso automatizado** futuro.

### 1.3 Origen del dato analizado

- **Bucket:** `tailoy-poc-s3-bucket-raw`
- **Ruta:** `tai-loy/maestro/raw/ASPRD.ha00/ha00_YYYYMMDD.csv`
- **Ejemplo analizado:** `ha00_20260930.csv` (lote del 2026-09-29)
- **Programa generador en AS/400:** `HA04006A`
- **Servicio de integración:** `QWSERVICE` (job `QZRCSRVS`, host-server de llamadas remotas / RFC)

---

## 2. Análisis del log (hallazgos reales)

### 2.1 Características del archivo

| Atributo | Valor |
|----------|-------|
| Formato | Texto delimitado por `\|` (pipe) |
| Campos | Ancho fijo con padding de espacios (archivo infla a ~3.9 MB con 2.474 registros) |
| Encoding | Texto plano exportado desde EBCDIC |
| Registros de datos | 2.474 (lote 2026-09-29) |
| Rango horario | 00:12 → 23:47 (corrió todo el día) |
| Columnas | 17 |

### 2.2 Estructura de columnas (tabla HA00)

| Idx | Campo | Significado | Rol en el análisis |
|-----|-------|-------------|--------------------|
| 0 | H0CIN | Programa/transacción origen (`SD040`) | **Origen** |
| 1 | H0COR | Correlativo del registro de error | Identificador |
| 2 | H0CER | Código de error / marca (`9999999`) | Marca de error |
| 3 | H0TR1 | Documento: tipo + número (`1FA...`, `2OT...`) | Clave de negocio |
| 4 | **H0TR2** | **Texto del error devuelto por SAP** | **Causa (campo clave)** |
| 5 | H0SAP | Nº de documento SAP creado (vacío = no se creó) | **Target** |
| 6 | H0EST | Estado (`1` = error pendiente) | Estado |
| 7 | H0FCR | Fecha de creación (YYYYMMDD) | Auditoría |
| 8 | H0HCR | Hora de creación (HHMMSS) | Auditoría |
| 9 | H0UCR | Usuario creación (`QWSERVICE`) | Auditoría |
| 10 | H0DCR | Job (`QZRCSRVS`) | Auditoría |
| 11 | H0PCR | Programa (`HA04006A`) | Auditoría |
| 12 | H0FUP | Fecha de actualización/reproceso | Reproceso (vacío = nunca) |
| 13 | H0HUP | Hora de actualización | Reproceso |
| 14 | H0UUP | Usuario actualización | Reproceso |
| 15 | H0DUP | Job actualización | Reproceso |
| 16 | H0PUP | Programa actualización | Reproceso |

**Hallazgo crítico:** `H0SAP` está **vacío en todos los registros** y `H0FUP/H0PUP` también → **ningún documento se creó en SAP y ninguno fue reprocesado**. Todo queda estancado hasta intervención manual.

### 2.3 Flujo origen → target

```
AS/400 (SD040 / HA04006A)
     │  envía documento vía RFC/servicio QWSERVICE
     ▼
SAP (intenta crear cliente / pedido / factura)
     │  valida contra datos maestros y reglas de negocio
     ▼
SAP RECHAZA  ──► devuelve motivo (H0TR2)
     │
     ▼
Log HA00  (H0TR2 = motivo, H0SAP vacío, H0EST = 1)
     │  exportado a S3 como CSV diario
     ▼
[NUEVO] Analizador + Alertas
```

El fallo **no es de conectividad** (la RFC funciona y SAP responde). Es de **completitud de datos maestros y reglas de negocio**.

### 2.4 Catálogo de errores por causa raíz

Totales del lote analizado (2.474 registros):

| # | Código causa raíz | Descripción (mensaje SAP) | Casos | % | Equipo responsable |
|---|-------------------|---------------------------|------:|--:|--------------------|
| 1 | `PARTNER_FUNCTIONS_FALTANTES` | No se puede determinar el pagador / solicitante / destinatario de mercancía / receptor de factura | 1.480 | 60% | Datos Maestros |
| 2 | `DATOS_CLIENTE_INCOMPLETOS` | Valor de Cliente es obligatorio `&5&6&7&8` (placeholders SAP sin resolver → mapeo origen no envió el valor) | 404 | 16% | Datos Maestros / Integración |
| 3 | `STOCK_INSUFICIENTE_ATP` | AL util. libre por debajo de N UND/BST/PQT/CA... | 337 | 14% | **Operaciones (alerta diferenciada)** |
| 4 | `DEUDOR_INEXISTENTE` | El deudor AZ... no existe | 130 | 5% | Datos Maestros |
| 5 | `CLIENTE_SIN_MAESTRO_VENTAS_KNVV` | Cliente N: Falta tabla maestra de clientes KNVV (falta vista de área de ventas) | 100 | 4% | Datos Maestros |
| 6 | `MATERIAL_BLOQUEADO` | Los datos de centro del material N están bloqueados por el usuario (INTEGRATION / PVALENTIN) | 22 | 1% | Transitorio (reprocesable) |
| 7 | `CUENTA_MAYOR_INEXISTENTE` | La cta. mayor AZ... no existe | 1 | <1% | Contabilidad / Config |
| — | `OTRO` | No clasificado | — | — | Revisión manual |

### 2.5 Insights clave para el diseño

1. **85% es el mismo problema de fondo** (categorías 1, 2, 4 y 5 = *cliente migrado incompleto en SAP*): 2.114 registros. Es sistemático, no casos aislados.
2. **Agrupar por cliente reduce el ruido**: los 4 partner-functions caen juntos por cada cliente → 1.480 líneas ≈ 370 clientes reales. Alertar por cliente, no por línea.
3. **Stock/ATP (14%) es ruido operativo** mezclado en el log de migración → debe ser **alerta diferenciada** (sigue en el flujo pero con tratamiento y destinatario propios).
4. **Cero reproceso hoy** → oportunidad clara de automatización.
5. Prefijos de documento (H0TR1): `2-0T` (1.669), `1-TI` (303), `1-3T` (227), `1-FA` (195), etc. — distintos tipos de transacción de venta.

---

## 3. Requerimientos

### 3.1 Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-01 | Detectar automáticamente nuevos lotes de error en CloudWatch (análisis nativo, sin prototipo local). | Alta |
| RF-02 | Clasificar cada error en una de las categorías de causa raíz del catálogo (§2.4). | Alta |
| RF-03 | Agrupar los errores por cliente afectado y por categoría, no por línea individual. | Alta |
| RF-04 | Diferenciar el error de **STOCK_INSUFICIENTE_ATP** como alerta separada, manteniéndolo dentro del flujo general de errores. | Alta |
| RF-05 | Enviar **una notificación por email** por lote, bien estructurada, usando **SES + SNS**, consolidada en un solo correo a la bandeja personal del responsable. | Alta |
| RF-06 | El correo debe incluir: resumen por categoría, conteo total, clientes afectados principales, y la alerta diferenciada de stock. | Alta |
| RF-07 | Definir umbrales de severidad (CRÍTICA / WARNING / INFO) por categoría y volumen. | Media |
| RF-08 | Dejar la base para reproceso automatizado de errores transitorios (material bloqueado, stock repuesto). | Baja (fase futura) |

### 3.2 Requerimientos no funcionales

| ID | Requerimiento |
|----|---------------|
| RNF-01 | Solución **nativa en AWS**, operada por CloudWatch (sin servidores propios). |
| RNF-02 | El análisis debe correr automáticamente al llegar un nuevo CSV al bucket. |
| RNF-03 | Las alertas no deben generar ruido: los errores transitorios/operativos no deben despertar al equipo de madrugada (severidad INFO). |
| RNF-04 | El código de clasificación debe ser mantenible y permitir agregar nuevas categorías de error sin reescribir todo. |
| RNF-05 | Idempotencia: reprocesar el mismo CSV no debe duplicar alertas. |

### 3.3 Restricciones conocidas

- El profile actual `tailoydev` (cuenta `971431176203`, SSO rol `tailoy-dlk-poc-read-only`) es **solo lectura**. Para desplegar recursos (Lambda, SNS, SES, alarmas) se requiere un **rol/perfil con permisos de escritura**. → **Pendiente de resolver antes de desplegar.**
- SES requiere **verificación del dominio o del correo destino** y, si está en sandbox, verificación también del remitente y destinatarios.

---

## 4. Diseño técnico en AWS

### 4.1 Arquitectura propuesta

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  S3  tailoy-poc-s3-bucket-raw                                         │
│  └─ tai-loy/maestro/raw/ASPRD.ha00/ha00_YYYYMMDD.csv                  │
│         │ (1) ObjectCreated event                                     │
│         ▼                                                             │
│  Lambda  "ha00-error-analyzer"                                        │
│   - parsea CSV (delimitador |, ancho fijo)                            │
│   - clasifica cada error por causa raíz (catálogo §2.4)              │
│   - agrupa por cliente + categoría                                    │
│   - separa alerta diferenciada STOCK_ATP                              │
│         │ (2) publica métricas                                        │
│         ▼                                                             │
│  CloudWatch  (métricas custom + Logs)                                 │
│   - namespace: TaiLoy/IntegracionAS400SAP                             │
│   - métricas por categoría y por severidad                            │
│         │ (3) evalúa umbrales                                         │
│         ▼                                                             │
│  CloudWatch Alarms  (una por severidad/categoría)                     │
│         │ (4) dispara                                                 │
│         ▼                                                             │
│  SNS  Topic "ha00-alertas"                                            │
│         │ (5) invoca                                                  │
│         ▼                                                             │
│  Lambda  "ha00-email" (SINTETIZADORA)                                 │
│   - calcula tablas/cifras en codigo (determinista)                   │
│   - llama a Bedrock (Claude Sonnet 5.5) para la NARRATIVA             │
│   - ensambla el correo (datos duros + narrativa IA)                  │
│   - fallback a plantilla si Bedrock falla                            │
│         │                                                             │
│         ▼                                                             │
│  SES  ->  bandeja personal (UN correo consolidado por lote)           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Componentes

| Componente | Servicio AWS | Responsabilidad |
|------------|--------------|-----------------|
| Disparador | S3 Event Notification | Detectar nuevo CSV y lanzar el análisis |
| Analizador | Lambda (Python) | Parsear, clasificar, agrupar, emitir métricas y logs |
| Observabilidad | CloudWatch Metrics + Logs | Almacenar conteos por categoría/severidad y evaluar reglas |
| Reglas de detección | CloudWatch Alarms / Metric Filters | Detectar automáticamente los tipos de error y disparar |
| Enrutamiento de alertas | SNS Topic | Punto único de fan-out de alertas |
| Síntesis del correo | Lambda (Python) + Amazon Bedrock | Calcular cifras en código y redactar la narrativa con IA (patrón híbrido) |
| Redacción (IA) | Amazon Bedrock — Claude Sonnet 5.5 | Resumen ejecutivo y próxima acción en lenguaje natural |
| Envío de correo | SES | Enviar un único email estructurado consolidado |
| Destino | Email (bandeja personal) | Recibir la alerta consolidada |

### 4.3 Detección en CloudWatch (clave del RF-01)

Dos enfoques combinables:

1. **Métricas custom desde la Lambda analizadora** (recomendado): la Lambda emite, por lote, una métrica por categoría (`PARTNER_FUNCTIONS_FALTANTES=1480`, `STOCK_INSUFICIENTE_ATP=337`, etc.) al namespace `TaiLoy/IntegracionAS400SAP`. Las **CloudWatch Alarms** evalúan umbrales sobre esas métricas.
2. **Metric Filters sobre CloudWatch Logs**: la Lambda escribe líneas de log estructuradas (JSON) por categoría; los **Metric Filters** cuentan patrones y alimentan alarmas. Útil como respaldo y para patrones nuevos no catalogados.

### 4.4 Umbrales y severidad (RF-07) — propuesta inicial a validar

| Categoría | Severidad | Regla de disparo (propuesta) |
|-----------|-----------|------------------------------|
| PARTNER_FUNCTIONS_FALTANTES | CRÍTICA | Siempre que haya ≥ 1 (o supere X% del lote) |
| DATOS_CLIENTE_INCOMPLETOS | CRÍTICA | ≥ 1 |
| DEUDOR_INEXISTENTE | WARNING | ≥ 1 |
| CLIENTE_SIN_MAESTRO_VENTAS_KNVV | WARNING | ≥ 1 |
| STOCK_INSUFICIENTE_ATP | INFO (alerta diferenciada) | Resumen aparte; no escala a crítica |
| MATERIAL_BLOQUEADO | INFO (transitorio) | Candidato a reproceso automático |
| CUENTA_MAYOR_INEXISTENTE | WARNING | ≥ 1 |
| OTRO | WARNING | ≥ 1 (requiere revisión / nueva categoría) |

> Los umbrales exactos (porcentajes, mínimos) se afinarán con el equipo. Pendiente de los "detalles adicionales" que el negocio dará sobre la alerta de stock.

### 4.5 Estructura del correo (RF-05, RF-06)

Un solo email por lote, con secciones:

1. **Encabezado:** fecha del lote, total de errores, nº de clientes afectados.
2. **Resumen por categoría:** tabla con causa raíz, conteo, % y equipo responsable.
3. **Alerta diferenciada — Stock/ATP:** sección propia con los documentos afectados por disponibilidad.
4. **Top clientes afectados:** cliente + categorías que lo afectan + nº de documentos.
5. **Siguiente acción sugerida** por categoría.
6. **Enlace** al CSV en S3 y a los logs/dashboard.

Flujo técnico: CloudWatch Alarm → SNS → Lambda sintetizadora → SES (correo HTML estructurado). La consolidación en **un único correo** se logra formateando en la Lambda a partir del resumen del lote (no un correo por alarma).

### 4.6 Síntesis del correo con IA — Amazon Bedrock (decisión de arquitectura)

La Lambda que arma el correo evoluciona de **formateadora rígida** a **sintetizadora**:
usa **Amazon Bedrock (Claude Sonnet 5.5)** para redactar la narrativa, manteniendo
las cifras calculadas en código. Validado end-to-end en la cuenta `971431176203`
(`us-east-1`, profile `tailoydev`).

#### Patrón híbrido: la IA redacta, el código manda los números

Regla de oro: **la IA no inventa ni recalcula cifras** (riesgo de alucinación sobre
datos de negocio).

- **El código calcula y renderiza** (determinista, auditable): totales, conteos por
  categoría, %, top clientes, tabla de severidades, sección de stock. Sale directo
  del JSON del analizador.
- **La IA redacta**: resumen ejecutivo (2-4 frases) y "próxima acción sugerida" por
  equipo responsable, en tono accionable. En el prompt se le pasan las cifras ya
  calculadas y se le prohíbe explícitamente generar otras.

#### Datos técnicos críticos (validados en la PoC — no omitir)

| Punto | Detalle |
|-------|---------|
| **Inference profile obligatorio** | Invocar siempre `us.anthropic.claude-sonnet-5-5` (inference profile, cross-region). El modelId plano `anthropic.claude-sonnet-5-5` **falla** con `ValidationException: on-demand throughput isn't supported`. |
| **SCP de la organización** | La org (`o-18nyn14y7h`, SCP `p-hhd712q9`) bloquea a propósito los *foundation-models* directos; en el playground aparece como *explicit deny*. El inference profile `us.*` sí está permitido. |
| **`temperature` deprecado** | Sonnet 5.5 deprecó `temperature` (y muy probablemente `top_p`). Pasarlo da `ValidationException`. En `inferenceConfig` enviar **solo `maxTokens`**. |
| **Parseo de la respuesta** | La respuesta puede traer bloques `reasoningContent` antes del texto. Al recorrer `output.message.content`, quedarse solo con los bloques que tengan clave `text`; no asumir que `content[0]` es el texto. |
| **Rendimiento (256 MB)** | Invocación completa ~1.6 s, init ~0.5 s, ~78 tokens in / 150 out para un resumen corto. Para 1 correo/día, costo y latencia despreciables. Timeout de Lambda 30 s suficiente. |

#### Resiliencia (requisito, no opcional)

- **Fallback a plantilla**: si Bedrock falla, da timeout o devuelve vacío, la Lambda
  cae a una narrativa plantillada determinista y **envía el correo igual**. La alerta
  nunca se bloquea por la IA (llamada envuelta en `try/except`).
- **Timeouts**: el cliente boto3 de Bedrock se configura por debajo del timeout de la
  Lambda (`connect_timeout=3s`, `read_timeout=12s`, `max_attempts=1` vs. Lambda 30 s).
- **Idempotencia (RNF-05)**: reprocesar el mismo CSV no debe duplicar correos.

#### Permiso IAM requerido

El rol de la Lambda sintetizadora necesita `bedrock:InvokeModel` sobre el inference
profile y los foundation-models subyacentes (por el cross-region del perfil `us.*`):

```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": [
    "arn:aws:bedrock:*:971431176203:inference-profile/us.anthropic.claude-sonnet-5-5",
    "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-5-5"
  ]
}
```

Variable de entorno de la Lambda: `MODEL_ID=us.anthropic.claude-sonnet-5-5`.

#### Diseño del prompt

- **System**: rol = "asistente de operaciones de datos maestros de Tai Loy que redacta
  alertas accionables para la integración AS/400 → SAP".
- **User**: inyecta el JSON del resumen del lote + instrucciones de salida (idioma
  español, longitud, secciones, mencionar equipos responsables por categoría, no
  inventar cifras). Salida en texto que el código incrusta en la plantilla del correo.

#### Modelos disponibles en la cuenta (alternativas)

Verificado con `list-inference-profiles` (todos ACTIVE como inference profile `us.*` /
`global.*`): Sonnet 5.5, Sonnet 5, Sonnet 4.5/4.6, Opus 4.1→5.5, Haiku 4.5, Fable
5/5.1. Si el volumen de correos crece y se busca abaratar, **Haiku 4.5** es la
alternativa económica para redacción (cambiar solo el parámetro `ModelId`).

#### Snippet de referencia (validado en la PoC)

```python
import boto3
MODEL_ID = "us.anthropic.claude-sonnet-5-5"   # inference profile, NO el modelId plano
rt = boto3.client("bedrock-runtime")
resp = rt.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    inferenceConfig={"maxTokens": 150},        # NO pasar 'temperature' (deprecado en 5.5)
)
# La respuesta puede traer bloques de reasoning; tomar solo los de texto:
text = "".join(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)
```

---

## 5. Decisiones tomadas

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| Canal de notificación | Email vía **SES + SNS**, consolidado en un solo correo | Pedido explícito del negocio |
| Dónde corre el análisis | **Nativo en AWS / CloudWatch**, sin prototipo local | Pedido explícito del negocio |
| Tratamiento de stock/ATP | **Alerta diferenciada** dentro del flujo general | Pedido explícito del negocio |
| Agrupación | Por cliente + categoría | Reduce 1.480 líneas a ~370 clientes reales |
| Redacción del correo | **Lambda sintetizadora con Bedrock (Claude Sonnet 5.5)**, patrón híbrido | IA redacta narrativa accionable; el código mantiene las cifras (determinista, auditable) |
| Invocación de Bedrock | **Inference profile `us.*`** (no modelId plano) | El modelId plano falla; la org bloquea foundation-models directos vía SCP |
| Infraestructura como código | **CloudFormation** (`infra/cloudformation.yaml`) | Versionable, autocontenida (código Lambda inline) |

## 6. Pendientes / decisiones abiertas

- [ ] Correo destino exacto y verificación en SES (¿dominio `tailoy.com.pe` o correo puntual?).
- [ ] ¿SES está en sandbox o producción en la cuenta? Afecta a qué destinatarios se puede enviar.
- [x] Perfil/rol con permisos de **escritura** para desplegar. **Resuelto**: profile `tailoydev` con `AWSAdministratorAccess`.
- [ ] Detalles adicionales del negocio sobre la **alerta diferenciada de stock** (qué incluir, a quién, umbral).
- [ ] Umbrales finales por categoría (porcentajes vs. mínimos absolutos).
- [ ] ¿Se requiere dashboard (QuickSight/Grafana/CloudWatch Dashboard) además del correo?
- [x] Región de despliegue. **Resuelto**: `us-east-1` (donde está el bucket).
- [x] Infraestructura como código. **Resuelto**: **CloudFormation** (`infra/cloudformation.yaml`).
- [x] Modelo de IA para la narrativa. **Resuelto**: Claude Sonnet 5.5 vía inference profile `us.anthropic.claude-sonnet-5-5`.

## 7. Fases de implementación

| Fase | Alcance | Estado |
|------|---------|--------|
| **Fase 0** | Documento de requerimientos y diseño (este archivo) | En curso |
| **Fase 1** | Analizador + clasificación + métricas CloudWatch + alarmas | Pendiente |
| **Fase 2** | SNS + Lambda sintetizadora (Bedrock + fallback) + SES (correo consolidado) | Pendiente |
| **Fase 3** | Alerta diferenciada de stock afinada con negocio | Pendiente |
| **Fase 4** | Reproceso automatizado de errores transitorios | Futuro |

---

## Anexo A — Comandos de referencia

Descarga del log para análisis (profile read-only):

```powershell
aws s3 cp "s3://tailoy-poc-s3-bucket-raw/tai-loy/maestro/raw/ASPRD.ha00/ha00_20260930.csv" ".\data\ha00_20260930.csv" --profile tailoydev
```

Verificación de identidad:

```powershell
aws sts get-caller-identity --profile tailoydev
```

Listar inference profiles de Sonnet 5.5 disponibles:

```powershell
aws bedrock list-inference-profiles --region us-east-1 --profile tailoydev `
  --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'sonnet-5-5')].{Id:inferenceProfileId,Status:status}" --output table
```

Probar la invocación (converse) con el inference profile:

```powershell
# messages.json: [{"role":"user","content":[{"text":"Responde: ok bedrock"}]}]
# infcfg.json:   {"maxTokens":50}
aws bedrock-runtime converse --region us-east-1 --profile tailoydev `
  --model-id "us.anthropic.claude-sonnet-5-5" `
  --messages file://messages.json --inference-config file://infcfg.json
```
