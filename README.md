# Sistema de Alertas — Errores de Integración AS/400 → SAP

Monitoreo y alertamiento automatizado de los errores que SAP devuelve cuando se
migran/integran clientes y documentos de ventas desde **AS/400 (iSeries)**. El
log de errores (tabla **HA00**) se exporta a S3 como CSV diario; esta solución lo
detecta, clasifica por causa raíz, emite métricas a CloudWatch y envía **un único
correo estructurado** vía **SNS + SES**.

> Repositorio: https://github.com/DiegoChu0434/KiroDay-TayLoy2026.git

## Arquitectura

```
S3 (nuevo CSV)
   └─(evento ObjectCreated)─> Lambda analizadora
                                 ├─ parsea + clasifica por causa raíz
                                 ├─ agrupa por cliente + categoría
                                 ├─ emite métricas a CloudWatch
                                 └─ publica resumen en SNS
                                        └─> Lambda formateadora ─> SES ─> 📧
   CloudWatch Alarms (errores críticos) ──┘
```

## Estructura del repositorio

```
.
├── README.md
├── .gitignore
├── docs/
│   └── especificaciones-alertas-integracion-as400-sap.md   # requerimientos + diseño
├── data/
│   └── ha00_20260930.csv                                   # dataset de ejemplo (log real)
├── src/
│   ├── analyzer/analyzer.py                                # Lambda analizadora (standalone)
│   └── email_formatter/email_formatter.py                  # Lambda formateadora (standalone)
├── infra/
│   └── cloudformation.yaml                                 # IaC: toda la infraestructura
├── tests/
│   └── test_classifier.py                                  # prueba del clasificador vs. dataset real
└── scripts/
    └── deploy.ps1                                          # despliegue con un comando
```

> El código de las Lambdas vive **dos veces** a propósito: la versión *standalone*
> en `src/` (legible, con docstrings, para desarrollo y pruebas) y una versión
> compacta **inline** dentro de `infra/cloudformation.yaml` (`ZipFile`) para que la
> plantilla sea autocontenida y se despliegue sin empaquetado. Ambas comparten la
> misma lógica de clasificación.

## Catálogo de errores (causas raíz)

| Categoría | Severidad | Equipo | Casos (lote ejemplo) |
|-----------|-----------|--------|---------------------:|
| PARTNER_FUNCTIONS_FALTANTES | CRÍTICA | Datos Maestros | 1.480 |
| DATOS_CLIENTE_INCOMPLETOS | CRÍTICA | Datos Maestros / Integración | 404 |
| STOCK_INSUFICIENTE_ATP | INFO (diferenciada) | Operaciones | 337 |
| DEUDOR_INEXISTENTE | WARNING | Datos Maestros | 130 |
| CLIENTE_SIN_MAESTRO_VENTAS_KNVV | WARNING | Datos Maestros | 100 |
| MATERIAL_BLOQUEADO | INFO (transitorio) | Reprocesable | 22 |
| CUENTA_MAYOR_INEXISTENTE | WARNING | Contabilidad | 1 |
| OTRO | WARNING | Revisión manual | — |

El **stock/ATP** se trata como **alerta diferenciada**: sigue dentro del flujo de
errores pero con sección y severidad propias, para no inflar la percepción de
fallas de migración.

## Despliegue

### Requisitos previos

- AWS CLI configurado con un profile con permisos de escritura (Lambda, IAM, SNS, SES, CloudWatch, CloudFormation).
- Región: `us-east-1` (donde está el bucket `tailoy-poc-s3-bucket-raw`).

### 1. Desplegar la infraestructura

```powershell
./scripts/deploy.ps1 -Profile tailoydev -Sender "tu-correo@dominio.com" -Recipient "tu-bandeja@dominio.com"
```

O manualmente:

```powershell
aws cloudformation deploy `
  --template-file infra/cloudformation.yaml `
  --stack-name ha00-alertas `
  --parameter-overrides SesSender="tu-correo@dominio.com" SesRecipient="tu-bandeja@dominio.com" `
  --capabilities CAPABILITY_NAMED_IAM `
  --region us-east-1 --profile tailoydev
```

### 2. Verificar las identidades en SES (paso obligatorio)

SES de esta cuenta está en **modo sandbox**. Tras el deploy, AWS envía un correo
de verificación al remitente y al destinatario. **Hay que hacer clic en el enlace
de ambos** antes de que se pueda enviar la alerta.

```powershell
aws ses list-identities --region us-east-1 --profile tailoydev
```

### 3. Conectar el evento de S3 (paso manual post-deploy)

Como el bucket `tailoy-poc-s3-bucket-raw` ya existe, la notificación `ObjectCreated`
que invoca la Lambda analizadora se configura una vez tras el deploy (CloudFormation
no modifica notificaciones de buckets preexistentes sin un *custom resource*). El
`ARN` de la Lambda está en los *Outputs* del stack. Ver `scripts/deploy.ps1` para
el comando `put-bucket-notification-configuration`.

## Pruebas

```powershell
python tests/test_classifier.py
```

Ejecuta el clasificador contra el dataset real `data/ha00_20260930.csv` y verifica
los conteos esperados por categoría.

## Pendientes / fases futuras

- Umbrales finales de severidad por categoría (afinar con negocio).
- Detalles adicionales de la alerta diferenciada de stock.
- Dashboard (CloudWatch/QuickSight/Grafana).
- Fase 4: reproceso automatizado de errores transitorios (material bloqueado, stock repuesto).

Ver `docs/especificaciones-alertas-integracion-as400-sap.md` para el detalle completo.
