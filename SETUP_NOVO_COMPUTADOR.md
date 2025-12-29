# Setup em Novo Computador

Quando voce mudar de computador ou usuario, siga estes passos para que o bot funcione corretamente.

## Problema

O `.venv` (ambiente virtual Python) e especifico de cada computador/usuario. Se voce transferir o projeto de outro computador, ele nao vai funcionar porque tem caminhos hardcoded.

Erro tipico:
```
Unable to create process using 'C:\Users\outrouser\...\python.exe'
O sistema nao pode encontrar o arquivo especificado.
```

## Solucao

### Passo 1: Verificar Python

Abra PowerShell e execute:

```powershell
python --version
```

Deve mostrar `Python 3.11+`. Se nao funcionar, baixe em: https://www.python.org/downloads/

**Importante:** Durante a instalacao, marque a opcao "Add Python to PATH"

### Passo 2: Executar Setup Automatico

Abra PowerShell **na pasta raiz do projeto** e execute:

```powershell
.\setup.ps1
```

Isso vai:
1. Verificar Python
2. Deletar `.venv` antigo (de outro usuario)
3. Criar novo `.venv` do zero
4. Instalar todas as dependencias

Aguarde 3-7 minutos ate terminar.

Saida esperada:
```
SETUP CONCLUIDO COM SUCESSO!
```

### Passo 3: Configurar `.env`

Se ainda nao tem, crie um arquivo `.env` na **raiz do projeto** com:

```env
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_ID=seu_phone_id
VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
SPREADSHEET_ID=seu_spreadsheet_id
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=seu_token_ngrok
NGROK_REGION=us
LOG_LEVEL=INFO
```

### Passo 4: Colocar `service_account.json`

Se ainda nao tem, coloque o arquivo `service_account.json` na **raiz do projeto**. Este arquivo contem as credenciais do Google Sheets.

### Passo 5: Iniciar o Servidor

```powershell
.\dev\start_webhook.ps1
```

Se vir a mensagem:
```
Servidor iniciando...
[ngrok] Webhook URL: https://xxxxx.ngrok-free.dev/webhook
```

Parabens! Está funcionando.

---

## Se Algo Deu Errado

### "Python nao esta instalado"

Baixe em: https://www.python.org/downloads/

Importante: Durante a instalacao, marque a opcao "Add Python to PATH"

### "Erro ao criar venv"

Feche todos os programas Python e VS Code, depois tente novamente:

```powershell
Remove-Item -Recurse -Force .\.venv
.\setup.ps1
```

### "ModuleNotFoundError: No module named 'fastapi'"

As dependencias nao foram instaladas. Execute novamente:

```powershell
.\setup.ps1
```

### Ainda da erro ao iniciar

Tente manualmente:

```powershell
# 1. Ativar venv
.\.venv\Scripts\Activate.ps1

# 2. Iniciar uvicorn
python -m uvicorn src.whatsapp_webhook:app --reload --port 8000
```

---

## Nota Importante

NAO commite na git:
- `.venv/` (ambiente virtual - ja no .gitignore)
- `.env` (credenciais - ja no .gitignore)
- `service_account.json` (credenciais - ja no .gitignore)

---

## Checklist

Apos setup completo:

- [ ] Python 3.11+ instalado
- [ ] `.\setup.ps1` executado com sucesso
- [ ] `.env` configurado com credenciais
- [ ] `service_account.json` na raiz do projeto
- [ ] `.\dev\start_webhook.ps1` inicia sem erros
- [ ] Bot responde a mensagens de teste

---

Pronto! Seu projeto está funcional em qualquer computador.
