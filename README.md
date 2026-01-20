# WhatsApp Scheduling Chatbot

WhatsApp chatbot for scheduling, rescheduling, and canceling appointments with Google Sheets backend.

## Overview

- Guided conversational menu in Portuguese
- Appointment scheduling via Google Sheets integration
- Automated 24-hour appointment reminders
- Daily summary reports for business owners
- Real-time appointment status management

## Key Technologies

- **Backend**: Python with Flask/FastAPI
- **Messaging**: WhatsApp Cloud API (Meta)
- **Database**: Google Sheets
- **Webhook Management**: Ngrok for local development
- **Service Management**: NSSM (Windows Service)

## Core Features

The system provides:
- **Interactive Menu System** with guided conversation flows
- **Smart Scheduling** with conflict detection and availability management
- **Automated Reminders** sent 24 hours before appointments
- **Appointment Management** for rescheduling and cancellations
- **Contact Management** with customer registration and history
- **Service Logging** with error tracking and execution logs
- **Google Sheets Integration** for easy data access and backup

## Getting Started

### Prerequisites
- Python 3.x
- WhatsApp Cloud API credentials (Meta for Developers)
- Google Sheets with proper configuration
- Ngrok account (for local development)

### Quick Setup (One-time)

```powershell
.\setup.ps1
```

Configure your `.env` file with required credentials:
```
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_ID=your_phone_id
VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
SPREADSHEET_ID=your_spreadsheet_id
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=your_ngrok_token
```

## Local Development

### Start Server with Automatic Ngrok

```powershell
.\dev\start_webhook.ps1
```

Wait until you see:
```
Servidor iniciando...
[ngrok] Webhook URL: https://xxxxx.ngrok-free.dev/webhook
```

Configure this URL in **Meta for Developers** > Settings > Configuration.

### Manual Alternative (without automatic ngrok)

```powershell
# Terminal 1:
.\dev\iniciar_servidor.ps1

# Terminal 2:
ngrok http 8000
```

### Test Conversational Flows

```powershell
python tests/test_fluxo_conversacional.py
```

Generates reports in: `tests/relatorio_testes_<timestamp>.txt`

## Production Deployment (Windows Service)

### Install Service (First Time)

See complete guide: [docs/CONFIGURAR_SERVICO_WINDOWS.md](docs/CONFIGURAR_SERVICO_WINDOWS.md)

Summary:
```powershell
# 1. Install NSSM (https://nssm.cc/download)
# 2. nssm install WhatsAppAgendadorBot
#    Configure Python path and arguments: src/whatsapp_webhook.py
# 3. nssm start WhatsAppAgendadorBot
```

### Update Code in Production

```powershell
.\deployment\atualizar_servico.ps1
```

Executes: stop service → git pull → install dependencies → restart service

### Monitor Service Logs

```powershell
powershell -Command "Get-Content 'logs\service_error.log' -Tail 20"
```

## Project Structure

```
whatsapp-chat-bot/
├── setup.ps1                   (initial setup)
├── dev/                        (development)
│   ├── start_webhook.ps1      (with automatic ngrok)
│   └── iniciar_servidor.ps1   (without ngrok)
├── deployment/                 (production)
│   └── atualizar_servico.ps1  (update service)
├── src/                        (main application code)
├── tests/                      (automated tests)
├── docs/                       (documentation)
└── logs/                       (execution logs)
```

## Google Sheets Configuration

**Appointments Sheet**: dia_semana, data, hora, nome_paciente, telefone, status, origem, observacoes

**Contacts Sheet**: telefone, nome, data_cadastro, origem, observacoes

**Reminders Sheet**: scheduled_iso, appointment_iso, appointment_date, appointment_time, telefone, paciente, tipo, sent_at, created_at, observacoes

## Documentation

- [New Computer Setup](SETUP_NOVO_COMPUTADOR.md) - When switching machines
- [Developer Guide](docs/GUIA_DESENVOLVEDOR.md) - Internal architecture
- [Windows Service Configuration](docs/CONFIGURAR_SERVICO_WINDOWS.md) - Production setup with NSSM
- [Test Plan](docs/PLANO_TESTES.md) - Testing strategy
- [Changelog](docs/CHANGELOG.md) - Version history and updates