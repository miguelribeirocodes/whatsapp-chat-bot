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
Contato
- Arquivo principal do fluxo: whatsapp_flow.py

WhatsApp Chat Bot (agendador)

Visão geral
-----------
Este projeto é um chatbot guiado para WhatsApp (sem IA) que permite agendar, reagendar e cancelar consultas usando Google Sheets como backend. O bot envia lembretes interativos para pacientes e um resumo diário para o proprietário/administrador.

Principais funcionalidades
-------------------------
- Menu guiado em português (Agendar, Reagendar, Cancelar, Sair).
- Cadastro no primeiro contato: pergunta o nome completo e salva em `Cadastros`.
- Persistência de agendamentos em `Agenda` e lembretes em `Lembretes` (Google Sheets).
- Envio de lembretes interativos (botões confirmar/cancelar) e marcação como enviados para evitar reenvios após reinício.
- Resumo diário para o proprietário configurável por horário.

Requisitos
---------
- Python 3.11+
- Contas e bibliotecas: ver `requirements.txt`.
- Conta de serviço do Google com acesso à planilha (arquivo `service_account.json`).
- Variáveis de ambiente:
  - `WHATSAPP_TOKEN` — token da API do WhatsApp.
  - `WHATSAPP_PHONE_ID` — id do telefone do WhatsApp Business.
  - `VERIFY_TOKEN` — token de verificação do webhook (opcional).
  - `SPREADSHEET_ID` — id da planilha no Google Sheets.

Estrutura das planilhas (abas esperadas)
-------------------------------------
- `Agenda` — colunas esperadas (exemplo): `dia_semana`, `data` (dd/mm/YYYY), `hora` (HH:MM), `nome_paciente`, `telefone`, `status`, `origem`, `observacoes`.
- `Cadastros` — colunas: `telefone`, `nome`, `data_cadastro`, `origem`, `observacoes`.
- `Lembretes` — colunas criadas pelo bot: `scheduled_iso`, `appointment_iso`, `appointment_date`, `appointment_time`, `telefone`, `paciente`, `tipo`, `sent_at`, `created_at`, `observacoes`.

Principais arquivos
-------------------
- `whatsapp_webhook.py`: webhook FastAPI, helpers de envio e handlers interativos.
- `whatsapp_flow.py`: fluxo conversacional e lógica de agendamento.
- `agenda_service.py`: integração com Google Sheets (Agenda, Cadastros, Lembretes) e utilitários.
- `messages.py`: centralização de mensagens padrão e constantes (personalize aqui para alterar textos).
- `scheduler.py`: agendador em memória para enviar lembretes e resumo diário.

Boas práticas e segurança
------------------------
- Nunca comite `service_account.json` nem credenciais. O `.gitignore` já inclui `service_account.json` e `.env`.
- Se for usar HTTPS/Deploy, prefira variáveis de ambiente e um gerenciador secreto.

Resolução de problemas comuns
----------------------------
- gspread Error 429 (quota exceeded): reduzir leituras em loops; o projeto já tem cache curto para leituras frequentes.
- Erros ao atualizar célula no Sheets: verificar permissões da conta de serviço e esquema de colunas.
- Erros de API do WhatsApp: verifique `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` e formato dos payloads (tamanhos/títulos).

Testes manuais
--------------
1) Envie uma mensagem inicial do seu número de teste para o webhook (via WhatsApp configurado) e confirme que o bot pergunta o nome.
2) Faça um agendamento por todo o fluxo e verifique se uma linha nova aparece em `Agenda` e `Lembretes`.
3) Simule a espera do lembrete (ou ajuste `REMINDER_HOURS_BEFORE` temporariamente) e verifique o envio do lembrete interativo.

Notas finais
-----------
- O repositório já foi inicializado e enviado para o remote que você forneceu.
- Para ajustes de texto, edite `messages.py` e reinicie o servidor.

Contato
-------
Proprietário/administrador: número configurado em `messages.py` (variável `CLINIC_OWNER_PHONE`).

Change log
----------
Veja `Change_Log.txt` para histórico de alterações e decisões importantes.
