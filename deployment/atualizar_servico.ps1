# Script para atualizar o servico WhatsApp Bot em producao
# Execute como Administrador

# Cores para output
$SUCCESS = "Green"
$ERROR_COLOR = "Red"
$INFO = "Cyan"
$WARN = "Yellow"

# Determinar diretorio do projeto (sobe um nível da pasta deployment/)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR

# Nome do servico NSSM
$SERVICE_NAME = "WhatsAppAgendadorBot"

Write-Host ""
Write-Host "========================================" -ForegroundColor $INFO
Write-Host "Atualizando servico em PRODUCAO" -ForegroundColor $INFO
Write-Host "========================================" -ForegroundColor $INFO
Write-Host ""

# Etapa 1: Verificar se servico existe
Write-Host "[1/5] Verificando servico NSSM..." -ForegroundColor $INFO
$serviceExists = (Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue)
if (-not $serviceExists) {
    Write-Host "ERRO: Servico $SERVICE_NAME nao encontrado" -ForegroundColor $ERROR_COLOR
    Write-Host "Certifique-se de que o servico foi criado com NSSM" -ForegroundColor $WARN
    exit 1
}
Write-Host "OK: Servico encontrado" -ForegroundColor $SUCCESS

# Etapa 2: Parar servico
Write-Host "[2/5] Parando servico..." -ForegroundColor $INFO
nssm stop $SERVICE_NAME
if ($?) {
    Write-Host "OK: Servico parado" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Falha ao parar servico" -ForegroundColor $ERROR_COLOR
    exit 1
}
Start-Sleep -Seconds 3

# Etapa 3: Atualizar codigo via Git
Write-Host "[3/5] Atualizando codigo via Git..." -ForegroundColor $INFO
Push-Location $PROJECT_DIR
git pull origin main
if (-not $?) {
    Write-Host "ERRO: Falha ao atualizar Git" -ForegroundColor $ERROR_COLOR
    Write-Host "Verifique sua conexao com Git" -ForegroundColor $WARN
    Pop-Location
    exit 1
}
Write-Host "OK: Codigo atualizado" -ForegroundColor $SUCCESS
Pop-Location

# Etapa 4: Instalar novas dependencias
Write-Host "[4/5] Atualizando dependencias Python..." -ForegroundColor $INFO
$VENV_PATH = Join-Path $PROJECT_DIR ".venv"
$PIP_EXE = Join-Path (Join-Path $VENV_PATH "Scripts") "pip.exe"

if (-not (Test-Path $PIP_EXE)) {
    Write-Host "ERRO: Ambiente virtual nao encontrado em $VENV_PATH" -ForegroundColor $ERROR_COLOR
    exit 1
}

& $PIP_EXE install -r "$PROJECT_DIR\requirements.txt" --upgrade --quiet
if ($?) {
    Write-Host "OK: Dependencias atualizadas" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Falha ao atualizar dependencias" -ForegroundColor $ERROR_COLOR
    Write-Host "Verifique o arquivo requirements.txt" -ForegroundColor $WARN
    exit 1
}

# Etapa 5: Reiniciar servico
Write-Host "[5/5] Reiniciando servico..." -ForegroundColor $INFO
nssm start $SERVICE_NAME
Start-Sleep -Seconds 5

$status = nssm status $SERVICE_NAME
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "OK: Servico reiniciado com sucesso" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Servico nao iniciou corretamente" -ForegroundColor $ERROR_COLOR
    Write-Host "Status: $status" -ForegroundColor $WARN
}

# Resultado
Write-Host ""
Write-Host "========================================" -ForegroundColor $SUCCESS
Write-Host "ATUALIZACAO CONCLUIDA!" -ForegroundColor $SUCCESS
Write-Host "========================================" -ForegroundColor $SUCCESS
Write-Host ""
Write-Host "Verificando logs:" -ForegroundColor $INFO
$LOG_FILE = Join-Path $PROJECT_DIR "logs\service_error.log"
Write-Host "Ultimas 10 linhas:" -ForegroundColor Gray
powershell -Command "Get-Content '$LOG_FILE' -Tail 10"
Write-Host ""
