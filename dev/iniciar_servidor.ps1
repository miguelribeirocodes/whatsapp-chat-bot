# Script para iniciar o servidor SEM ngrok automático - VERSÃO DINÂMICA
# IMPORTANTE: Este script desabilita completamente o ngrok automático
# Funciona em qualquer computador/usuário

# Determinar diretório do projeto (sobe um nível da pasta dev/)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$VENV_PATH = Join-Path $PROJECT_DIR ".venv"
$PYTHON_EXE = Join-Path $VENV_PATH "Scripts" "python.exe"
$VENV_ACTIVATE = Join-Path $VENV_PATH "Scripts" "Activate.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando Servidor WhatsApp Bot" -ForegroundColor Cyan
Write-Host "Projeto: $PROJECT_DIR" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se venv existe
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "❌ Erro: Ambiente virtual não encontrado!" -ForegroundColor Red
    Write-Host "Execute primeiro:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# Parar processos antigos
Write-Host "🔄 Parando processos antigos..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue | Out-Null
Stop-Process -Name uvicorn -Force -ErrorAction SilentlyContinue | Out-Null
Start-Sleep -Seconds 2

# Ativar venv
Write-Host "✓ Ativando ambiente virtual" -ForegroundColor Green
& $VENV_ACTIVATE
if (-not $?) {
    Write-Host "❌ Erro ao ativar venv" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "🚀 Servidor iniciando..." -ForegroundColor Green
Write-Host "⚠️  NGROK está DESABILITADO" -ForegroundColor Yellow
Write-Host "Configure a URL manualmente no Meta for Developers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Iniciar uvicorn SEM reload (para evitar re-importacoes do ngrok)
& $PYTHON_EXE -m uvicorn src.whatsapp_webhook:app --host 0.0.0.0 --port 8000
