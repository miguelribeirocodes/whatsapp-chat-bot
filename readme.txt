Como usar

- Objetivo: servidor webhook FastAPI para fluxo de agendamento (Agendar / Reagendar / Cancelar) integrado ao Google Sheets.

Pré-requisitos
- Python 3.8+

- Como iniciar o venv:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv
.\.venv\Scripts\Activate.ps1

- Instale dependências: pip install -r requirements.txt
- Crie um arquivo .env com: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, VERIFY_TOKEN e SPREADSHEET_ID.

Rodando localmente (desenvolvimento)
- Inicie o servidor FastAPI:
  .venv\Scripts\uvicorn.exe whatsapp_webhook:app --reload --port 8000
- Em outro terminal exponha local: ngrok http 8000
- Configure no Meta for Developers:
  - Callback URL: https://<SEU_NGROK>.ngrok-free.dev/webhook
  - Verify token: valor de VERIFY_TOKEN no .env

Testes locais (terminal)
- Para testar o fluxo em terminal execute: python whatsapp_flow.py (usa Google Sheets para slots).

Notas
- O armazenamento de agendamentos é feito na planilha definida em SPREADSHEET_ID.
- Em produção, persista sessões (ex.: Redis) e use HTTPS público fixo.

Contato
- Arquivo principal do fluxo: whatsapp_flow.py
- Webhook FastAPI: whatsapp_webhook_fixed.py
