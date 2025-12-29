# WhatsApp Bot Agendador

Chatbot para WhatsApp que permite agendar, reagendar e cancelar consultas. Backend em Google Sheets.

## Visao Geral

- Menu guiado em portugues
- Agenda de consultas em Google Sheets
- Lembretes automaticos 24h antes
- Resumo diario para proprietario

---

## GUIA RAPIDO

### 1. Setup Inicial (uma unica vez)

```powershell
.\setup.ps1
```

Configure o arquivo `.env` com suas credenciais:
```
WHATSAPP_TOKEN=seu_token
WHATSAPP_PHONE_ID=seu_phone_id
VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
SPREADSHEET_ID=seu_spreadsheet_id
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=seu_token_ngrok
```

---

## DESENVOLVIMENTO LOCAL (Debug)

### Iniciar servidor com ngrok automatico

```powershell
.\dev\start_webhook.ps1
```

Aguarde ate ver:
```
Servidor iniciando...
[ngrok] Webhook URL: https://xxxxx.ngrok-free.dev/webhook
```

Configure essa URL no **Meta for Developers** > Settings > Configuration.

### Ou sem ngrok (manual)

```powershell
# Terminal 1:
.\dev\iniciar_servidor.ps1

# Terminal 2:
ngrok http 8000
```

### Testar fluxos conversacionais

```powershell
python tests/test_fluxo_conversacional.py
```

Gera relatorios em: `tests/relatorio_testes_<timestamp>.txt`

---

## PRODUCAO (Servico Windows)

### Instalar servico (primeira vez)

Veja guia completo: [docs/CONFIGURAR_SERVICO_WINDOWS.md](docs/CONFIGURAR_SERVICO_WINDOWS.md)

Resumo:
```powershell
# 1. Instalar NSSM (https://nssm.cc/download)
# 2. nssm install WhatsAppAgendadorBot
#    Configure path do Python, argumentos: src/whatsapp_webhook.py
# 3. nssm start WhatsAppAgendadorBot
```

### Atualizar codigo em producao

```powershell
.\deployment\atualizar_servico.ps1
```

Faz: parar -> git pull -> instalar dependencias -> reiniciar

### Monitorar logs

```powershell
powershell -Command "Get-Content 'logs\service_error.log' -Tail 20"
```

---

## Estrutura do Projeto

```
Chat Bot Agendador/
├── setup.ps1                   (setup inicial)
├── dev/                        (desenvolvimento)
│   ├── start_webhook.ps1      (com ngrok automatico)
│   └── iniciar_servidor.ps1   (sem ngrok)
├── deployment/                 (producao)
│   └── atualizar_servico.ps1  (atualizar servico)
├── src/                        (codigo principal)
├── tests/                      (testes automatizados)
├── docs/                       (documentacao)
└── logs/                       (logs de execucao)
```

## Google Sheets - Abas Esperadas

**Agenda**: dia_semana, data, hora, nome_paciente, telefone, status, origem, observacoes

**Cadastros**: telefone, nome, data_cadastro, origem, observacoes

**Lembretes**: scheduled_iso, appointment_iso, appointment_date, appointment_time, telefone, paciente, tipo, sent_at, created_at, observacoes

---

## Documentacao Completa

- [Setup Novo Computador](SETUP_NOVO_COMPUTADOR.md) - Quando mudar de PC
- [Guia Desenvolvedor](docs/GUIA_DESENVOLVEDOR.md) - Arquitetura interna
- [Configurar Servico Windows](docs/CONFIGURAR_SERVICO_WINDOWS.md) - Setup producao com NSSM
- [Plano de Testes](docs/PLANO_TESTES.md) - Estrategia de testes
- [Changelog](docs/CHANGELOG.md) - Historico de alteracoes