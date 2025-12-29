# Script para iniciar o webhook com ngrok - VERSÃO DINÂMICA
# Funciona em qualquer computador/usuário

# Determinar diretório do projeto (sobe um nível da pasta dev/)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$VENV_PATH = Join-Path $PROJECT_DIR ".venv"
$PYTHON_EXE = Join-Path (Join-Path $VENV_PATH "Scripts") "python.exe"
$VENV_ACTIVATE = Join-Path (Join-Path $VENV_PATH "Scripts") "Activate.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando Bot WhatsApp com ngrok" -ForegroundColor Cyan
Write-Host "Projeto: $PROJECT_DIR" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se venv existe
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "ERRO: Ambiente virtual nao encontrado!" -ForegroundColor Red
    Write-Host "Execute primeiro:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# Parar processos antigos
Write-Host "Parando processos antigos..." -ForegroundColor Yellow
Stop-Process -Name ngrok -Force -ErrorAction SilentlyContinue | Out-Null
Stop-Process -Name uvicorn -Force -ErrorAction SilentlyContinue | Out-Null
Stop-Process -Name python -Force -ErrorAction SilentlyContinue | Out-Null
Start-Sleep -Seconds 2

# Ativar venv
Write-Host "Ativando ambiente virtual" -ForegroundColor Green
& $VENV_ACTIVATE
if (-not $?) {
    Write-Host "ERRO: Erro ao ativar venv" -ForegroundColor Red
    exit 1
}

# Iniciar uvicorn
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Servidor iniciando..." -ForegroundColor Green
Write-Host "Aguarde 5-10 segundos para o ngrok conectar" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $PYTHON_EXE -m uvicorn src.whatsapp_webhook:app --reload --port 8000

# Note: Este script continuara rodando enquanto uvicorn estiver ativo
# Para parar: CTRL+C
