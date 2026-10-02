<#
.SYNOPSIS
  Despliega el stack de alertas de errores de integracion AS/400 -> SAP.

.DESCRIPTION
  1. Valida y despliega la plantilla CloudFormation (infra/cloudformation.yaml).
  2. Muestra los outputs del stack.
  3. Imprime el comando para conectar el evento S3 -> Lambda analizadora
     (paso manual, porque el bucket ya existe).

  SES esta en sandbox: tras el deploy hay que verificar manualmente el remitente
  y el destinatario (clic en el correo que envia AWS).

.EXAMPLE
  ./scripts/deploy.ps1 -Profile tailoydev -Sender "a@dominio.com" -Recipient "b@dominio.com"
#>
param(
    [Parameter(Mandatory = $true)][string]$Profile,
    [Parameter(Mandatory = $true)][string]$Sender,
    [Parameter(Mandatory = $true)][string]$Recipient,
    [string]$Region = "us-east-1",
    [string]$StackName = "ha00-alertas",
    [string]$BucketName = "tailoy-poc-s3-bucket-raw",
    [string]$ErrorPrefix = "tai-loy/maestro/raw/ASPRD.ha00/",
    [int]$BedrockMaxTokens = 2000
)

$ErrorActionPreference = "Stop"
$templatePath = Join-Path $PSScriptRoot "..\infra\cloudformation.yaml"

Write-Host "== Validando plantilla ==" -ForegroundColor Cyan
aws cloudformation validate-template `
    --template-body "file://$templatePath" `
    --region $Region --profile $Profile | Out-Null

Write-Host "== Desplegando stack '$StackName' ==" -ForegroundColor Cyan
aws cloudformation deploy `
    --template-file $templatePath `
    --stack-name $StackName `
    --parameter-overrides `
        SesSender="$Sender" `
        SesRecipient="$Recipient" `
        RawBucketName="$BucketName" `
        ErrorPrefix="$ErrorPrefix" `
        BedrockMaxTokens="$BedrockMaxTokens" `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $Region --profile $Profile

Write-Host "== Outputs del stack ==" -ForegroundColor Cyan
$outputs = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region --profile $Profile `
    --query "Stacks[0].Outputs" | ConvertFrom-Json

$outputs | ForEach-Object { Write-Host ("  {0} = {1}" -f $_.OutputKey, $_.OutputValue) }

$analyzerArn = ($outputs | Where-Object { $_.OutputKey -eq "AnalyzerFunctionArn" }).OutputValue

Write-Host "`n== PASO MANUAL 1: verificar identidades SES ==" -ForegroundColor Yellow
Write-Host "  Revisa la bandeja de '$Sender' y '$Recipient' y haz clic en el enlace de verificacion."
Write-Host "  Estado:  aws ses list-identities --region $Region --profile $Profile"

Write-Host "`n== PASO MANUAL 2: conectar evento S3 -> Lambda analizadora ==" -ForegroundColor Yellow
Write-Host @"
  aws s3api put-bucket-notification-configuration ``
    --bucket $BucketName ``
    --notification-configuration '{
      \"LambdaFunctionConfigurations\": [{
        \"LambdaFunctionArn\": \"$analyzerArn\",
        \"Events\": [\"s3:ObjectCreated:*\"],
        \"Filter\": {\"Key\": {\"FilterRules\": [{\"Name\": \"prefix\", \"Value\": \"$ErrorPrefix\"}]}}
      }]
    }' ``
    --region $Region --profile $Profile
"@

Write-Host "`nDespliegue completado." -ForegroundColor Green
