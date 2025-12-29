# Script de Setup - Inicializa o projeto em qualquer computador/usuario
# Execute uma unica vez em cada computador novo

# Cores para output
$SUCCESS = "Green"
$ERROR_COLOR = "Red"
$INFO = "Cyan"
$WARN = "Yellow"

# Determinar diretorio do projeto
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PATH = Join-Path $PROJECT_DIR ".venv"

Write-Host ""
Write-Host "========================================" -ForegroundColor $INFO
Write-Host "Setup do Chat Bot Agendador" -ForegroundColor $INFO
Write-Host "========================================" -ForegroundColor $INFO
Write-Host ""
Write-Host "Projeto: $PROJECT_DIR" -ForegroundColor Gray
Write-Host ""

# Etapa 1: Verificar Python
Write-Host "[1/4] Verificando Python..." -ForegroundColor $INFO
$PYTHON_VERSION = python --version 2>&1
if ($?) {
    Write-Host "OK: $PYTHON_VERSION encontrado" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Python nao esta instalado ou nao esta no PATH" -ForegroundColor $ERROR_COLOR
    Write-Host "Baixe em: https://www.python.org/downloads/" -ForegroundColor $WARN
    exit 1
}

# Etapa 2: Deletar venv antigo (se existir de outro usuario)
if (Test-Path $VENV_PATH) {
    Write-Host ""
    Write-Host "[2/4] Removendo ambiente virtual antigo..." -ForegroundColor $INFO
    Write-Host "Deletando $VENV_PATH" -ForegroundColor Gray
    try {
        Remove-Item -Recurse -Force $VENV_PATH
        Write-Host "OK: Deletado com sucesso" -ForegroundColor $SUCCESS
    } catch {
        Write-Host "ERRO: Erro ao deletar venv" -ForegroundColor $ERROR_COLOR
        Write-Host "Feche todos os programas Python/VS Code e tente novamente" -ForegroundColor $WARN
        exit 1
    }
} else {
    Write-Host "[2/4] Nenhum venv antigo encontrado" -ForegroundColor $INFO
}

# Etapa 3: Criar novo venv
Write-Host ""
Write-Host "[3/4] Criando novo ambiente virtual..." -ForegroundColor $INFO
Write-Host "Isso pode levar 1-2 minutos..." -ForegroundColor Gray
python -m venv $VENV_PATH
if ($?) {
    Write-Host "OK: Ambiente virtual criado" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Erro ao criar venv" -ForegroundColor $ERROR_COLOR
    exit 1
}

# Etapa 4: Instalar dependencias
Write-Host ""
Write-Host "[4/4] Instalando dependencias..." -ForegroundColor $INFO
Write-Host "Isso pode levar 2-5 minutos dependendo da conexao..." -ForegroundColor Gray

# Ativar venv
$VENV_ACTIVATE = Join-Path $VENV_PATH "Scripts" "Activate.ps1"
& $VENV_ACTIVATE

# Atualizar pip primeiro
Write-Host "Atualizando pip..." -ForegroundColor Gray
python -m pip install --upgrade pip --quiet

# Instalar dependencias
Write-Host "Instalando requirements.txt..." -ForegroundColor Gray
pip install -r requirements.txt --quiet

if ($?) {
    Write-Host "OK: Dependencias instaladas" -ForegroundColor $SUCCESS
} else {
    Write-Host "ERRO: Erro ao instalar dependencias" -ForegroundColor $ERROR_COLOR
    exit 1
}

# Sucesso!
Write-Host ""
Write-Host "========================================" -ForegroundColor $SUCCESS
Write-Host "SETUP CONCLUIDO COM SUCESSO!" -ForegroundColor $SUCCESS
Write-Host "========================================" -ForegroundColor $SUCCESS
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor $INFO
Write-Host "1. Configure o arquivo .env com suas credenciais:" -ForegroundColor Gray
Write-Host "   - WHATSAPP_TOKEN" -ForegroundColor Gray
Write-Host "   - WHATSAPP_PHONE_ID" -ForegroundColor Gray
Write-Host "   - SPREADSHEET_ID (Google Sheets)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Inicie o servidor com:" -ForegroundColor Gray
Write-Host "   .\start_webhook.ps1" -ForegroundColor $WARN
Write-Host ""
Write-Host "3. Configure o webhook no Meta for Developers" -ForegroundColor Gray
Write-Host ""
Write-Host "Para mais detalhes, veja README.md" -ForegroundColor Gray
Write-Host ""
