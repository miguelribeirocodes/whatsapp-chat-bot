# Guia: Hospedar Bot no Google Cloud

Este guia documenta o processo completo de hospedar o bot WhatsApp na Google Cloud Platform.

## Índice

1. [Criar VM](#criar-vm)
2. [Configurar Servidor](#configurar-servidor)
3. [Firewall](#firewall)
4. [Webhook](#webhook)
5. [Troubleshooting](#troubleshooting)

---

## Criar VM

### Passo 1: Acessar Google Cloud Console

1. Acesse [cloud.google.com](https://cloud.google.com)
2. Clique em **"Get started for free"**
3. Faça login com sua conta Google
4. Aceite os termos (cartão é necessário, mas não será cobrado no free tier)

### Passo 2: Criar Instância

1. Vá para **Compute Engine → Instâncias de VM**
2. Clique em **"Criar instância"**
3. Configure:
   - **Nome**: `whatsapp-bot`
   - **Região**: `us-central1` (free tier)
   - **Zona**: `us-central1-a`
   - **Tipo de máquina**: `e2-micro` (deve aparecer "Free tier eligible")
   - **Sistema operacional**: `Ubuntu 22.04 LTS`
   - **Disco permanente**: `30 GB` (padrão)

4. Desative:
   - ❌ Logging
   - ❌ Monitoramento
   - ❌ Snapshots automáticos

5. Clique em **"Criar"**

### Passo 3: Acessar via SSH

Na lista de instâncias, clique no botão **SSH** para abrir um terminal no navegador.

---

## Configurar Servidor

### Passo 1: Atualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

### Passo 2: Clonar Repositório

```bash
git clone git@github.com:miguelribeirocodes/whatsapp-chat-bot.git
cd whatsapp-chat-bot
```

(Use SSH key para não pedir senha)

### Passo 3: Configurar Ambiente

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Passo 4: Adicionar Credenciais

Você precisa fazer upload de dois arquivos:

1. **`.env`** - Variáveis de ambiente
2. **`service_account.json`** - Credenciais do Google Sheets

```bash
# Editar .env
nano .env
```

Cole:
```
WHATSAPP_TOKEN=seu_token
WHATSAPP_PHONE_ID=seu_phone_id
VERIFY_TOKEN=seu_verify_token
SPREADSHEET_ID=seu_spreadsheet_id
NGROK_ENABLED=false
LOG_LEVEL=INFO
```

Salve: `Ctrl+X` → `Y` → `Enter`

**Importante:** Se o `service_account.json` não estiver no repositório, faça upload via SCP do seu PC:

```powershell
# No PowerShell do seu PC
scp "C:\caminho\service_account.json" user@IP_DA_VM:~/whatsapp-chat-bot/
```

---

## Firewall

### Abrir Porta 8000

1. Acesse [Google Cloud Firewall](https://console.cloud.google.com/networking/firewalls)
2. Clique em **"CREATE FIREWALL RULE"**
3. Configure:
   - **Name**: `allow-webhook-8000`
   - **Direction of traffic**: `Ingress`
   - **Source IP ranges**: `0.0.0.0/0`
   - **Protocols and ports**:
     - ☑️ TCP
     - Porta: `8000`
4. Clique em **"Create"**

---

## Webhook

### Opção A: URL Fixa (Produção)

Use o IP externo da VM diretamente:

```
http://IP_EXTERNO:8000/webhook
```

Exemplo: `http://136.119.212.152:8000/webhook`

**Vantagens:**
- Funciona 24/7
- Não muda
- Estável

**Desvantagens:**
- Sem HTTPS (não é problema para Meta)

### Opção B: ngrok (Desenvolvimento)

Use ngrok para testar localmente:

```bash
# Instalar ngrok
sudo snap install ngrok

# Configurar autenticação
ngrok config add-authtoken SEU_TOKEN_AQUI

# Iniciar túnel
ngrok http 8000
```

Vai gerar URL tipo: `https://xxxx-xxxx.ngrok-free.app`

**Vantagens:**
- HTTPS automático
- Útil para desenvolvimento local

**Desvantagens:**
- URL muda a cada reinício
- Precisa deixar ngrok rodando
- Pode desligar se VM desligar

---

### Configurar no Meta for Developers

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Vá para sua app do WhatsApp
3. Selecione **Settings → Configuration**
4. Em **Webhook URL**, cole:
   ```
   http://136.119.212.152:8000/webhook
   ```
   (ou a URL do ngrok se usando)

5. Em **Verify Token**, cole o token do seu `.env`:
   ```
   OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
   ```

6. Clique em **"Verify and Save"**

### Ativar Webhook Fields

Ainda na página de Webhooks:

1. Procure por **"Webhook Fields"** ou **"Campos do webhook"**
2. Ative:
   - ☑️ `messages` (receber mensagens)
   - ☑️ `message_template_status_update` (confirmação)
   - ☑️ Outros que precisar

3. Clique em **"Save"**

---

## Rodar o Servidor

### Opção A: Systemd (Automático - Recomendado)

```bash
# Criar arquivo de serviço
sudo nano /etc/systemd/system/whatsapp-bot.service
```

Cole:
```ini
[Unit]
Description=WhatsApp Chat Bot
After=network.target

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/home/seu_usuario/whatsapp-chat-bot
Environment="PATH=/home/seu_usuario/whatsapp-chat-bot/venv/bin"
ExecStart=/home/seu_usuario/whatsapp-chat-bot/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Salve e execute:
```bash
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-bot
sudo systemctl start whatsapp-bot
sudo systemctl status whatsapp-bot
```

### Opção B: Manual (Desenvolvimento)

```bash
source venv/bin/activate
python -m uvicorn src.whatsapp_webhook:app --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

### Webhook não valida

**Sintoma:** "Não foi possível validar a URL de callback"

**Solução:**
1. Verifique se a porta 8000 está aberta no firewall
2. Teste localmente: `curl http://localhost:8000/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=SEU_TOKEN`
3. Teste pelo IP externo: `curl http://IP_EXTERNO:8000/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=SEU_TOKEN`
4. Se o IP não responde, firewall não está configurado

### Não recebe mensagens

**Sintoma:** Bot recebe mas não responde

**Solução:**
1. Verifique se os "Webhook Fields" estão ativados no Meta
2. Verifique o VERIFY_TOKEN está correto
3. Veja os logs: `sudo journalctl -u whatsapp-bot -n 50 --no-pager`

### Credenciais do Google Sheets

**Sintoma:** `FileNotFoundError: service_account.json`

**Solução:**
1. O arquivo deve estar na raiz do projeto: `/home/user/whatsapp-chat-bot/service_account.json`
2. Atualize `.gitignore` para permitir upload: comente a linha `service_account.json`
3. Faça git push e git pull na VM

### Arquivo main.py não existe

**Sintoma:** `src/main.py: No such file or directory`

**Solução:**
- O arquivo deve ser criado como ponto de entrada
- Se não existir, crie: `/home/user/whatsapp-chat-bot/src/main.py`
- Veja o arquivo de exemplo no repositório

---

## Monitorar Logs

```bash
# Ver últimas linhas
sudo journalctl -u whatsapp-bot -n 50 --no-pager

# Ver em tempo real
sudo journalctl -u whatsapp-bot -f

# Ver por data
sudo journalctl -u whatsapp-bot --since "2025-12-30" --until "2025-12-31"
```

---

## Parar/Reiniciar

```bash
# Parar
sudo systemctl stop whatsapp-bot

# Reiniciar
sudo systemctl restart whatsapp-bot

# Status
sudo systemctl status whatsapp-bot
```

---

## Custos

- **VM e2-micro**: Gratuito (1 por mês)
- **Transferência de dados**: 1 GB/mês gratuito
- **Armazenamento**: 30 GB gratuito
- **Total**: 0 (dentro do free tier)

---

**Última atualização:** 30/12/2025
