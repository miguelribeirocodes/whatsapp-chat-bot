# WhatsApp Bot Agendador

Chatbot guiado para WhatsApp que permite agendar, reagendar e cancelar consultas usando Google Sheets como backend.

## 🎯 Visão Geral

Um servidor webhook FastAPI para fluxo de agendamento (Agendar / Reagendar / Cancelar) integrado ao Google Sheets. O bot:
- Oferece menu guiado em português
- Registra cadastros de pacientes na primeira interação
- Persiste agendamentos em planilha Google Sheets
- Envia lembretes interativos com botões de confirmação/cancelamento
- Envia resumo diário para o proprietário/administrador

## 📋 Pré-requisitos

- **Python 3.11+**
- **Git** (para controle de versão)
- **Google Service Account** com acesso a Google Sheets
- **WhatsApp Business Account** com acesso à Cloud API

### Setup Inicial

```powershell
# 1. Criar ambiente virtual
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
# Crie um arquivo .env na raiz com:
# WHATSAPP_TOKEN=seu_token
# WHATSAPP_PHONE_ID=seu_phone_id
# VERIFY_TOKEN=seu_verify_token
# SPREADSHEET_ID=seu_spreadsheet_id
# NGROK_ENABLED=true
# NGROK_AUTH_TOKEN=seu_token_ngrok
# NGROK_REGION=us
```

## 🚀 Rodando Localmente (Desenvolvimento)

### Com ngrok automático (RECOMENDADO)

```bash
# 1. Ative o ambiente virtual
.\.venv\Scripts\Activate.ps1

# 2. Configure .env
# NGROK_ENABLED=true

# 3. Inicie o servidor
.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --reload --port 8000
```

A URL pública será exibida nos logs com prefixo `[ngrok] Webhook URL: https://...`

Configure essa URL no **Meta for Developers** como Callback URL.

### Sem ngrok (manual)

```bash
# Terminal 1: Inicie servidor FastAPI
.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --reload --port 8000

# Terminal 2: Crie túnel ngrok
ngrok http 8000

# Configure a URL do ngrok no Meta for Developers
```

## 🧪 Testes Automatizados

O projeto inclui suite de testes que simula conversas **sem enviar mensagens reais** para WhatsApp.

```bash
# Executar testes
python tests/test_fluxo_conversacional.py

# Resultados (gerados automaticamente):
# - tests/relatorio_testes_<timestamp>.txt (formato legível)
# - tests/relatorio_testes_<timestamp>.json (formato estruturado)
```

**Cobertura:**
- ✅ Fluxos válidos (happy path)
- ✅ Inputs inválidos (robustez)
- ✅ Alternância entre fluxos diferentes
- ✅ Edge cases (strings vazias, caracteres especiais, etc.)

Para detalhes sobre como adicionar novos testes, veja [tests/README.md](tests/README.md).

## 📁 Estrutura do Projeto

```
Chat Bot Agendador/
├── README.md                  (este arquivo)
├── requirements.txt           (dependências Python)
├── .env                       (variáveis de ambiente - NÃO commitar)
├── service_account.json       (credenciais Google - NÃO commitar)
│
├── src/                       (código principal)
│   ├── whatsapp_webhook.py   (API FastAPI)
│   ├── whatsapp_flow.py      (lógica conversacional)
│   ├── agenda_service.py     (Google Sheets)
│   ├── scheduler.py          (lembretes e resumos)
│   ├── ngrok_service.py      (túnel automático)
│   ├── messages.py           (textos padrão)
│   ├── constants.py          (constantes)
│   ├── flow_helpers.py       (funções auxiliares)
│   ├── logging_config.py     (configuração logs)
│   └── __init__.py
│
├── tests/                     (testes automatizados)
│   ├── README.md            (guia de testes)
│   ├── test_fluxo_conversacional.py
│   └── relatorio_testes_*.{json,txt}
│
├── docs/                      (documentação)
│   ├── CONFIGURAR_SERVICO_WINDOWS.md
│   ├── GUIA_DESENVOLVEDOR.md
│   ├── PLANO_TESTES.md
│   └── CHANGELOG.md
│
└── logs/                      (logs de execução)
    ├── app.log
    ├── service_output.log
    └── service_error.log
```

## 🗄️ Configuração do Google Sheets

### Abas Esperadas

**Agenda** - Colunas:
- `dia_semana`, `data` (dd/mm/YYYY), `hora` (HH:MM)
- `nome_paciente`, `telefone`, `status`, `origem`, `observacoes`

**Cadastros** - Colunas:
- `telefone`, `nome`, `data_cadastro`, `origem`, `observacoes`

**Lembretes** - Colunas (criadas automaticamente):
- `scheduled_iso`, `appointment_iso`, `appointment_date`, `appointment_time`
- `telefone`, `paciente`, `tipo`, `sent_at`, `created_at`, `observacoes`

## 🔧 Serviço Windows com NSSM

Para rodar em produção como serviço Windows:

```powershell
# 1. Instalar NSSM
# Download em: https://nssm.cc/download

# 2. Instalar serviço
nssm install WhatsAppAgendadorBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\src\whatsapp_webhook.py"
nssm set WhatsAppAgendadorBot AppDirectory "C:\path\to\project"
nssm set WhatsAppAgendadorBot AppLogOn "DOMAIN\USERNAME" "PASSWORD"

# 3. Configurar .env para produção
# NGROK_ENABLED=false
# Configure URL fixa no Meta for Developers

# 4. Iniciar serviço
nssm start WhatsAppAgendadorBot

# 5. Verificar logs
type logs\service_output.log
```

Para atualizar código:
```powershell
nssm stop WhatsAppAgendadorBot
# Atualizar arquivos Python
nssm start WhatsAppAgendadorBot
```

## 📈 Escalabilidade - Múltiplos Bots

Quando tiver domínio próprio e múltiplos bots, há três estratégias:

### Opção 1: Múltiplos Endpoints (RECOMENDADO)

```python
@app.post("/webhook/bot{bot_id}")
async def webhook_bot(bot_id: int, request: dict):
    # Identifica qual bot baseado no ID
    # Carrega configuração específica do bot
    # Processa mensagem com lógica dedicada
```

**Vantagens:** Fácil de monitorar, logs separados, escalável.

### Opção 2: Webhook Único com Roteamento

```python
@app.post("/webhook")
async def webhook(request: dict):
    phone_id = request.get("entry")[0].get("changes")[0].get("value").get("metadata").get("phone_number_id")
    if phone_id == "BOT_1_PHONE_ID":
        # Processa bot 1
```

**Vantagens:** Um único endpoint.

### Opção 3: Subdomínios

```
bot1.seu-dominio.com/webhook
bot2.seu-dominio.com/webhook
bot3.seu-dominio.com/webhook
```

**Vantagens:** Isolamento completo.

## 🔍 Resolução de Problemas

| Problema | Solução |
|----------|---------|
| `Error 429 quota exceeded` | Reduzir leituras em loops (já tem cache) |
| Erro ao atualizar Sheets | Verificar permissões da conta de serviço |
| Erro WhatsApp API | Verificar `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_ID` |
| Webhook não recebe mensagens | Verificar se NGROK_ENABLED=true e URL no Meta |

## 📚 Documentação Adicional

- [Guia do Desenvolvedor](docs/GUIA_DESENVOLVEDOR.md) - Arquitetura e padrões
- [Configuração Windows](docs/CONFIGURAR_SERVICO_WINDOWS.md) - Setup completo como serviço
- [Plano de Testes](docs/PLANO_TESTES.md) - Estratégia de testes
- [Changelog](docs/CHANGELOG.md) - Histórico de alterações

## 🚀 Próximas Etapas

1. Quando tiver clientes pagando, compre domínio próprio
2. Implemente múltiplos bots usando Opção 1
3. Configure CI/CD para deployments automáticos
4. Adicione autenticação de usuários

## 📞 Contato

Proprietário/administrador: configurado em `src/messages.py` (variável `CLINIC_OWNER_PHONE`)

## 📄 Licença

Sem especificação no projeto.

---

**Última atualização:** 2025-12-22
Para mais detalhes, veja a documentação em `docs/`
