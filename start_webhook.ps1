# Script para iniciar o webhook com ngrok e mostrar URL para configurar no WhatsApp

# Matar processos antigos
Write-Host "Parando processos antigos..." -ForegroundColor Yellow
Stop-Process -Name ngrok -Force -ErrorAction SilentlyContinue
Stop-Process -Name uvicorn -Force -ErrorAction SilentlyContinue
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Iniciando servidor..." -ForegroundColor Green

# Ativar venv
.\.venv\Scripts\Activate.ps1

# Iniciar uvicorn
Write-Host "`n" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Servidor iniciando..." -ForegroundColor Cyan
Write-Host "Aguarde 5-10 segundos para o ngrok conectar" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --reload --port 8000

# Note: Este script continuará rodando enquanto uvicorn estiver ativo
# Para parar: CTRL+C
