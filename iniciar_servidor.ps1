# Script para iniciar o servidor webhook SEM ngrok automático
# IMPORTANTE: Este script desabilita completamente o ngrok automático

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando Servidor WhatsApp Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Parar processos antigos
Write-Host "Parando processos antigos..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue | Out-Null
Stop-Process -Name uvicorn -Force -ErrorAction SilentlyContinue | Out-Null
Start-Sleep -Seconds 2

# Ativar venv
Write-Host "Ativando ambiente virtual..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Servidor iniciando..." -ForegroundColor Green
Write-Host "NGROK esta DESABILITADO" -ForegroundColor Yellow
Write-Host "Configure a URL no WhatsApp:" -ForegroundColor Cyan
Write-Host "https://legalistic-unable-rob.ngrok-free.dev/webhook" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Iniciar uvicorn SEM reload (para evitar re-importacoes do ngrok)
.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --host 127.0.0.1 --port 8000
