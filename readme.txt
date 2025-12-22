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

Desenvolvimento com ngrok automatizado (recomendado)
- O projeto agora inclui ngrok_service.py que cria o túnel automaticamente ao iniciar
- Configure no .env:
  NGROK_ENABLED=true
  NGROK_AUTH_TOKEN=seu_token_aqui (obter em https://dashboard.ngrok.com/)
  NGROK_REGION=us
- Inicie o servidor (o túnel será criado automaticamente):
  .venv\Scripts\uvicorn.exe whatsapp_webhook:app --reload --port 8000
- A URL pública será exibida nos logs com o prefixo "[ngrok] Webhook URL: https://..."
- Configure no Meta for Developers com essa URL

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

Serviço Windows com NSSM
------------------------
Para rodar como serviço Windows (produção):
1) Instale NSSM (Non-Sucking Service Manager): https://nssm.cc/download
2) Configure com sua conta de usuário (não System):
   nssm install WhatsAppAgendadorBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\whatsapp_webhook.py"
   nssm set WhatsAppAgendadorBot AppDirectory "C:\path\to\project"
   nssm set WhatsAppAgendadorBot AppLogOn "DOMAIN\USERNAME" "PASSWORD"
3) Para produção, desabilitar ngrok no .env:
   NGROK_ENABLED=false
4) Inicie o serviço:
   nssm start WhatsAppAgendadorBot
5) Verifique os logs:
   type logs\service_output.log

Para atualizar o código em produção:
1) Pare o serviço: nssm stop WhatsAppAgendadorBot
2) Atualize os arquivos Python
3) Reinicie: nssm start WhatsAppAgendadorBot

Escalabilidade - Múltiplos bots em produção
---------------------------------------------
Quando tiver múltiplos bots e um domínio próprio, há três estratégias recomendadas:

OPÇÃO 1: Múltiplos endpoints (RECOMENDADO)
- Melhor para: organização e escalabilidade
- Estrutura:
  * /webhook/bot1 → redireciona para lógica do bot 1
  * /webhook/bot2 → redireciona para lógica do bot 2
  * /webhook/bot3 → redireciona para lógica do bot 3
- Implementação:
  @app.post("/webhook/bot{bot_id}")
  async def webhook_bot(bot_id: int, request: dict):
      # Identifica qual bot baseado no ID
      # Carrega configuração específica do bot
      # Processa mensagem com lógica dedicada
- Vantagens:
  * Cada bot tem endpoint único
  * Fácil de monitorar e debugar
  * Logs separados por bot
  * Escalável para N bots
- No Meta for Developers: configure Callback URL como https://seu-dominio.com/webhook/bot1

OPÇÃO 2: Webhook único com roteamento
- Melhor para: bots com comportamento semelhante
- Estrutura:
  * /webhook recebe todas as mensagens
  * Identifica qual bot por metadados (número de telefone, campo custom, etc)
  * Roteia para lógica apropriada
- Implementação:
  @app.post("/webhook")
  async def webhook(request: dict):
      phone_id = request.get("entry")[0].get("changes")[0].get("value").get("metadata").get("phone_number_id")
      if phone_id == "BOT_1_PHONE_ID":
          # Processa bot 1
      elif phone_id == "BOT_2_PHONE_ID":
          # Processa bot 2
- Vantagens:
  * Apenas um endpoint
  * Ideal se bots usam mesmo código base
- Desvantagem: mais difícil de manter com bots muito diferentes

OPÇÃO 3: Subdomínios
- Melhor para: bots completamente independentes
- Estrutura:
  * bot1.seu-dominio.com/webhook
  * bot2.seu-dominio.com/webhook
  * bot3.seu-dominio.com/webhook
  * Cada subdomínio aponta para instância/porta diferente
- Vantagens:
  * Isolamento completo
  * Fácil de deployar/escalar
- Desvantagem: requer mais infraestrutura

RECOMENDAÇÃO: Usar Opção 1 (múltiplos endpoints) em um único servidor/app FastAPI.

Desenvolvimento em ngrok vs Produção em domínio próprio
-------------------------------------------------------
- Desenvolvimento: NGROK_ENABLED=true cria túnel automático (URL muda a cada restart)
- Produção: NGROK_ENABLED=false e configure webhook com domínio próprio (URL fixa)
- Token de autenticação ngrok (NGROK_AUTH_TOKEN):
  * Sem token: URL ngrok aleatória, ideal para testes rápidos
  * Com token: permite configurar domínio fixo (requer plano pago ngrok)

Notas finais
-----------
- O repositório já foi inicializado e enviado para o remote que você forneceu.
- Para ajustes de texto, edite `messages.py` e reinicie o servidor.
- Plano futuro: quando tiver clientes pagando, compre um domínio e implemente multi-bot usando Opção 1.

Contato
-------
Proprietário/administrador: número configurado em `messages.py` (variável `CLINIC_OWNER_PHONE`).

Change log
----------
Veja `Change_Log.txt` para histórico de alterações e decisões importantes.
