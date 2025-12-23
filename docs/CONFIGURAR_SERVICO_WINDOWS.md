# Configurar Bot como Serviço do Windows usando NSSM

Este guia mostra como configurar o bot de agendamento para rodar automaticamente como um serviço do Windows usando NSSM (Non-Sucking Service Manager).

## Pré-requisitos

- Windows 10 ou superior
- Python 3.11 instalado
- Bot já testado e funcionando manualmente
- Permissões de Administrador

---

## Passo 1: Baixar e Instalar NSSM

1. Acesse: https://nssm.cc/download
2. Baixe a versão mais recente (ex: nssm-2.24.zip)
3. Extraia o arquivo ZIP
4. Copie `nssm.exe` da pasta `win64` para `C:\Tools\nssm\nssm.exe`
5. Adicione `C:\Tools\nssm` ao PATH do Windows (opcional, facilita uso)

---

## Passo 2: Encontrar o Caminho Real do Python

**IMPORTANTE:** O Python precisa ser o executável REAL, não o alias da Windows Store.

Abra o Prompt de Comando e execute:

```cmd
python -c "import sys; print(sys.executable)"
```

Exemplo de saída:
```
C:\Users\User\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe
```

**Copie este caminho completo** - você vai precisar dele na configuração.

---

## Passo 3: Criar Pasta de Logs

```cmd
mkdir "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs"
```

---

## Passo 4: Configurar o Serviço com NSSM

Abra o **Prompt de Comando como Administrador** e execute:

```cmd
cd C:\Tools\nssm
nssm install WhatsAppAgendadorBot
```

Uma janela GUI será aberta. Configure **EXATAMENTE** desta forma:

### Aba Application

- **Path:** Cole o caminho real do Python obtido no Passo 2
  - Exemplo: `C:\Users\User\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`
  - ⚠️ **NÃO use:** `C:\Users\User\AppData\Local\Microsoft\WindowsApps\python.exe` (não funciona em serviços)

- **Startup directory:** `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador`

- **Arguments:** `src/whatsapp_webhook.py`

### Aba Details

- **Display name:** `WhatsApp Agendador Bot`
- **Description:** `Bot de agendamento via WhatsApp`
- **Startup type:** `Automatic` (para iniciar com o Windows)

### Aba Log on

⚠️ **IMPORTANTE:** Não use "Local System account"

- Selecione: **"This account"**
- **Account:** `.\User` (ou seu nome de usuário do Windows)
- **Password:** [sua senha do Windows]
- **Confirm:** [sua senha do Windows novamente]

**Por quê?** A conta Local System não tem acesso aos arquivos do OneDrive, credentials.json e .env.

### Aba I/O

- **Output (stdout):** `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_output.log`
- **Error (stderr):** `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_error.log`

### Aba File rotation (opcional, mas recomendado)

- **Rotate files:** Marque
- **Restrict rotation to files bigger than:** `10240` KB (10MB)
- **Replace existing Output and Error files:** Marque

Clique em **Install service**.

---

## Passo 5: Iniciar o Serviço

No Prompt de Comando como Administrador:

```cmd
cd C:\Tools\nssm
nssm start WhatsAppAgendadorBot
```

Aguarde 5-10 segundos e verifique o status:

```cmd
nssm status WhatsAppAgendadorBot
```

Deve retornar: `SERVICE_RUNNING`

---

## Passo 6: Verificar se Está Funcionando

### Verificar logs:

```cmd
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
powershell -Command "Get-Content 'logs\service_error.log' -Tail 30"
```

**Procure por estas linhas no final do log:**

✅ `INFO:     Uvicorn running on http://0.0.0.0:8000` - Servidor iniciou com sucesso
✅ `[startup] Slots inicializados com sucesso!` - Slots carregados
✅ `[scheduler] Scheduled job` - Jobs agendados

**NÃO deve ter:**
❌ `KeyboardInterrupt`
❌ `Exception`
❌ `Error`
❌ Loop de reinicializações repetidas

### Testar o bot:

Envie uma mensagem "Oi" para o número do WhatsApp configurado e veja se o bot responde.

---

## Comandos Úteis de Gerenciamento

Todos os comandos devem ser executados como Administrador em `C:\Tools\nssm`:

```cmd
# Ver status
nssm status WhatsAppAgendadorBot

# Parar serviço
nssm stop WhatsAppAgendadorBot

# Iniciar serviço
nssm start WhatsAppAgendadorBot

# Reiniciar serviço
nssm restart WhatsAppAgendadorBot

# Editar configuração
nssm edit WhatsAppAgendadorBot

# Remover serviço
nssm remove WhatsAppAgendadorBot confirm

# Ver últimas 20 linhas do log de erro
powershell -Command "Get-Content 'c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_error.log' -Tail 20"

# Ver últimas 50 linhas do log de output
powershell -Command "Get-Content 'c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_output.log' -Tail 50"
```

---

## Atualizar o Código do Serviço

Quando você fizer alterações no código ou atualizar via Git:

### Processo Manual

```cmd
# 1. Parar o serviço
nssm stop WhatsAppAgendadorBot

# 2. Atualizar código
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
git pull origin main

# 3. Atualizar dependências (se necessário)
pip install -r requirements.txt --upgrade

# 4. Testar manualmente antes de subir (RECOMENDADO)
python -m uvicorn src.whatsapp_webhook:app --host 0.0.0.0 --port 8000
# Aguarde ver "Uvicorn running on http://0.0.0.0:8000"
# Pressione Ctrl+C para parar

# 5. Reiniciar serviço
nssm start WhatsAppAgendadorBot

# 6. Verificar logs
powershell -Command "Get-Content 'logs\service_error.log' -Tail 20"
```

### Script Automatizado

Crie o arquivo `atualizar_servico.bat`:

```batch
@echo off
echo ========================================
echo  ATUALIZANDO WHATSAPP BOT
echo ========================================
echo.

echo [1/5] Parando servico...
nssm stop WhatsAppAgendadorBot
timeout /t 3 /nobreak >nul

echo [2/5] Atualizando codigo via Git...
cd /d "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
git pull origin main

echo [3/5] Atualizando dependencias...
pip install -r requirements.txt --upgrade --quiet

echo [4/5] Reiniciando servico...
nssm start WhatsAppAgendadorBot
timeout /t 5 /nobreak >nul

echo [5/5] Verificando status e logs...
nssm status WhatsAppAgendadorBot
echo.
echo Ultimas 15 linhas do log:
powershell -Command "Get-Content 'logs\service_error.log' -Tail 15"

echo.
echo ========================================
echo  ATUALIZACAO CONCLUIDA!
echo ========================================
pause
```

Salve em: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\atualizar_servico.bat`

Para usar: Clique com botão direito > **Executar como administrador**

---

## Solução de Problemas

### Problema 1: "Acesso negado" ao executar comandos NSSM

**Causa:** Não está rodando como Administrador

**Solução:**
- Feche o Prompt de Comando
- Pressione Windows, digite `cmd`
- Clique com botão direito > "Executar como administrador"

---

### Problema 2: Serviço para imediatamente após iniciar

**Causa:** Caminho do Python está errado (usando alias da Windows Store)

**Solução:**
```cmd
# Obter caminho correto
python -c "import sys; print(sys.executable)"

# Atualizar NSSM
nssm stop WhatsAppAgendadorBot
nssm set WhatsAppAgendadorBot Application "<caminho-correto-aqui>"
nssm start WhatsAppAgendadorBot
```

---

### Problema 3: Erro "Can't open service!"

**Causa:** Serviço não existe ou nome está errado

**Solução:**
```cmd
# Listar todos os serviços NSSM
sc query type= service state= all | findstr /i "whatsapp"

# Se não aparecer, precisa instalar novamente:
nssm install WhatsAppAgendadorBot
```

---

### Problema 4: Google Sheets não funciona (erro de autenticação)

**Causa:** Serviço rodando com conta Local System que não tem acesso aos arquivos

**Solução:**
```cmd
nssm edit WhatsAppAgendadorBot
```
- Vá na aba "Log on"
- Mude para "This account"
- Digite sua conta de usuário e senha
- Clique "Edit service"
- Reinicie o serviço

---

### Problema 5: Token do WhatsApp expira (erro 401)

**Causa:** Access Token do WhatsApp tem validade de 60 dias

**Solução:**
1. Acesse o Facebook Developers
2. Gere um novo token permanente
3. Atualize no arquivo `.env`
4. Reinicie o serviço:
```cmd
nssm restart WhatsAppAgendadorBot
```

---

### Problema 6: Serviço fica reiniciando em loop

**Causa:** Arquivo `whatsapp_webhook.py` não tem o bloco `if __name__ == "__main__"` com `uvicorn.run()`

**Verificar:** O final do arquivo deve ter:
```python
if __name__ == "__main__":
    import uvicorn
    logger.info("[main] Starting Uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### Problema 7: "ModuleNotFoundError" após reorganização do projeto

**Causa:** Após mover os arquivos para a pasta `src/`, os argumentos do NSSM precisam ser atualizados

**Solução:**
```cmd
# Parar o serviço
nssm stop WhatsAppAgendadorBot

# Atualizar os argumentos
nssm set WhatsAppAgendadorBot AppParameters "src/whatsapp_webhook.py"

# Reiniciar o serviço
nssm start WhatsAppAgendadorBot

# Verificar logs
powershell -Command "Get-Content 'logs\service_error.log' -Tail 20"
```

---

## Monitoramento

### Ver logs em tempo real:

```cmd
powershell -Command "Get-Content 'c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_error.log' -Wait -Tail 20"
```

Pressione `Ctrl+C` para sair.

### Verificar se porta 8000 está em uso:

```cmd
netstat -ano | findstr :8000
```

### Ver serviço no Gerenciador de Serviços do Windows:

1. Pressione `Windows + R`
2. Digite `services.msc`
3. Procure por "WhatsApp Agendador Bot"
4. Clique com botão direito > Propriedades para ver detalhes

---

## Checklist de Validação

Após configurar o serviço, confirme:

- [ ] `nssm status WhatsAppAgendadorBot` retorna `SERVICE_RUNNING`
- [ ] Log mostra `INFO:     Uvicorn running on http://0.0.0.0:8000`
- [ ] Log mostra `[startup] Slots inicializados com sucesso!`
- [ ] Não há exceções ou erros nos logs
- [ ] Bot responde a mensagens de teste no WhatsApp
- [ ] Schedulers estão rodando (procure por `[scheduler]` nos logs)
- [ ] Serviço reinicia automaticamente após reiniciar o computador

---

## Próximos Passos

1. ✅ Configure backup automático do código (Git)
2. ✅ Configure backup do Google Sheets (Google Takeout ou Apps Script)
3. ✅ Documente o processo de renovação do token do WhatsApp
4. ✅ Configure monitoramento de uptime (ex: UptimeRobot, Pingdom)
5. ✅ Teste o comportamento em caso de falha (reinício automático)

---

## Notas Importantes

- O serviço inicia automaticamente com o Windows (se configurado como Automatic)
- Logs são rotacionados automaticamente quando atingem 10MB (se configurado)
- O scheduler diário roda à meia-noite (00:01) para criar novos slots
- O resumo diário é enviado às 07:00
- Lembretes são enviados 24h antes do agendamento às 10:00
