# 🖥️ Setup em Novo Computador

Quando você mudar de computador ou usuario, siga estes passos para que o bot funcione corretamente.

## 🚨 Problema

O `.venv` (ambiente virtual Python) é específico de cada computador/usuário. Se você transferir o projeto de outro computador, ele não vai funcionar porque tem caminhos hardcoded.

**Erro típico:**
```
Unable to create process using 'C:\Users\outrouser\...\python.exe'
O sistema não pode encontrar o arquivo especificado.
```

## ✅ Solução

### Passo 1: Verificar Python

Abra PowerShell e execute:

```powershell
python --version
```

Deve mostrar `Python 3.11+`. Se não funcionar, baixe em: https://www.python.org/downloads/

### Passo 2: Executar Setup Automático

Abra PowerShell **na pasta do projeto** e execute:

```powershell
.\setup.ps1
```

Isso vai:
1. ✓ Verificar Python
2. ✓ Deletar `.venv` antigo (de outro usuário)
3. ✓ Criar novo `.venv` do zero
4. ✓ Instalar todas as dependências

Aguarde 3-7 minutos até terminar.

**Saída esperada:**
```
✅ SETUP CONCLUÍDO COM SUCESSO!
```

### Passo 3: Configurar `.env`

Se ainda não tem, crie um arquivo `.env` na **raiz do projeto** com:

```env
# WhatsApp Cloud API
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_ID=seu_phone_id
VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz

# Google Sheets
SPREADSHEET_ID=seu_spreadsheet_id

# ngrok (desenvolvimento)
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=seu_token_ngrok
NGROK_REGION=us

# Logs
LOG_LEVEL=INFO
```

### Passo 4: Colocar `service_account.json`

Se ainda não tem, coloque o arquivo `service_account.json` na **raiz do projeto**. Este arquivo contém as credenciais do Google Sheets.

### Passo 5: Iniciar o Servidor

```powershell
.\start_webhook.ps1
```

Se vir a mensagem:
```
🚀 Servidor iniciando...
[ngrok] Webhook URL: https://xxxxx.ngrok-free.dev/webhook
```

Parabéns! ✅ Está funcionando.

---

## 🔧 Se Algo Deu Errado

### "Python não está instalado"

Baixe em: https://www.python.org/downloads/

**Importante:** Durante a instalação, marque a opção **"Add Python to PATH"**

### "Erro ao criar venv"

Feche todos os programas Python e VS Code, depois tente novamente:

```powershell
Remove-Item -Recurse -Force .\.venv
.\setup.ps1
```

### "ModuleNotFoundError: No module named 'fastapi'"

As dependências não foram instaladas. Execute novamente:

```powershell
.\setup.ps1
```

### Ainda dá erro ao iniciar

Tente manualmente:

```powershell
# 1. Ativar venv
.\.venv\Scripts\Activate.ps1

# 2. Iniciar uvicorn
python -m uvicorn src.whatsapp_webhook:app --reload --port 8000
```

---

## 📝 Nota Importante

**NÃO commite na git:**
- `.venv/` (ambiente virtual - já no .gitignore)
- `.env` (credenciais - já no .gitignore)
- `service_account.json` (credenciais - já no .gitignore)

---

## 🎯 Checklist

Após setup completo:

- [ ] Python 3.11+ instalado
- [ ] `.\setup.ps1` executado com sucesso
- [ ] `.env` configurado com credenciais
- [ ] `service_account.json` na raiz do projeto
- [ ] `.\start_webhook.ps1` inicia sem erros
- [ ] Bot responde a mensagens de teste

---

**Pronto!** Seu projeto está funcional em qualquer computador.
