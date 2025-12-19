# Configurar Bot como Serviço do Windows

Este guia mostra como configurar o bot de agendamento para rodar automaticamente como um serviço do Windows.

## Método 1: Usando NSSM (Recomendado)

NSSM (Non-Sucking Service Manager) é a forma mais simples de transformar qualquer aplicação em serviço do Windows.

### Passo 1: Baixar NSSM

1. Acesse: https://nssm.cc/download
2. Baixe a versão mais recente (ex: nssm-2.24.zip)
3. Extraia o arquivo ZIP
4. Copie `nssm.exe` da pasta `win64` para uma localização permanente (ex: `C:\nssm\nssm.exe`)

### Passo 2: Criar o Serviço

Abra o **Prompt de Comando como Administrador** e execute:

```cmd
cd C:\nssm
nssm install WhatsAppAgendadorBot
```

Uma janela GUI será aberta. Configure:

**Aba Application:**
- **Path**: Caminho completo do Python (ex: `C:\Python311\python.exe`)
  - Para encontrar: execute `where python` no cmd
- **Startup directory**: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador`
- **Arguments**: `whatsapp_webhook.py`

**Aba Details:**
- **Display name**: `WhatsApp Agendador Bot`
- **Description**: `Bot de agendamento via WhatsApp para Clínica X`
- **Startup type**: `Automatic` (inicia com Windows)

**Aba Log on:**
- Deixe como padrão (Local System account) OU
- Use sua conta de usuário se precisar acessar arquivos do OneDrive

**Aba I/O:**
- **Output (stdout)**: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_output.log`
- **Error (stderr)**: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_error.log`

Clique em **Install service**.

### Passo 3: Criar Pasta de Logs

```cmd
mkdir "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs"
```

### Passo 4: Gerenciar o Serviço

**Iniciar o serviço:**
```cmd
nssm start WhatsAppAgendadorBot
```

**Parar o serviço:**
```cmd
nssm stop WhatsAppAgendadorBot
```

**Reiniciar o serviço:**
```cmd
nssm restart WhatsAppAgendadorBot
```

**Ver status:**
```cmd
nssm status WhatsAppAgendadorBot
```

**Remover o serviço:**
```cmd
nssm remove WhatsAppAgendadorBot confirm
```

**Editar configuração:**
```cmd
nssm edit WhatsAppAgendadorBot
```

### Passo 5: Verificar Logs

Após iniciar, verifique os arquivos de log:
- `logs\service_output.log` - saída normal do programa
- `logs\service_error.log` - erros e exceções

Procure pela linha:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Se aparecer, o serviço está funcionando!

---

## Método 2: Usando Gerenciador de Tarefas do Windows

Alternativa mais simples para testes, mas menos robusta.

### Criar Script de Inicialização

1. Crie um arquivo `iniciar_bot.bat`:

```batch
@echo off
cd /d "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
python whatsapp_webhook.py >> logs\bot.log 2>&1
```

2. Salve em: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\iniciar_bot.bat`

### Configurar no Agendador de Tarefas

1. Abra **Agendador de Tarefas** (Task Scheduler)
2. Clique em **Criar Tarefa Básica**
3. Nome: `WhatsApp Bot Agendador`
4. Gatilho: **Quando o computador iniciar**
5. Ação: **Iniciar um programa**
6. Programa: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\iniciar_bot.bat`
7. Marque: **Executar com privilégios mais altos**
8. Na aba **Configurações**, marque: **Se a tarefa falhar, reiniciar a cada: 1 minuto**

---

## Método 3: Usando Windows Services (Avançado)

Para criar um serviço Windows nativo em Python, usando `pywin32`.

### Instalar pywin32

```cmd
pip install pywin32
```

### Criar arquivo de serviço

Crie `whatsapp_service.py`:

```python
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import time

class WhatsAppBotService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WhatsAppAgendadorBot"
    _svc_display_name_ = "WhatsApp Agendador Bot"
    _svc_description_ = "Serviço de agendamento via WhatsApp para Clínica X"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Diretório do projeto
        project_dir = r"c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
        os.chdir(project_dir)

        # Executar whatsapp_webhook.py
        while self.running:
            try:
                self.process = subprocess.Popen(
                    [sys.executable, "whatsapp_webhook.py"],
                    cwd=project_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # Aguardar até o serviço ser parado
                while self.running:
                    if self.process.poll() is not None:
                        # Processo terminou inesperadamente, reiniciar
                        time.sleep(5)
                        break
                    time.sleep(1)

            except Exception as e:
                servicemanager.LogErrorMsg(f"Erro no serviço: {str(e)}")
                time.sleep(10)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WhatsAppBotService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(WhatsAppBotService)
```

### Instalar o serviço

```cmd
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
python whatsapp_service.py install
```

### Gerenciar o serviço

```cmd
# Iniciar
python whatsapp_service.py start

# Parar
python whatsapp_service.py stop

# Reiniciar
python whatsapp_service.py restart

# Remover
python whatsapp_service.py remove
```

Ou use `services.msc` (Serviços do Windows) para gerenciar visualmente.

---

## Recomendação

Para **testes iniciais**: Use **Método 1 (NSSM)** - é o mais simples e confiável.

Para **produção**: Continue com NSSM ou migre para **Método 3** se precisar de mais controle.

---

## Atualizar o Código do Serviço

Quando você fizer alterações no código ou atualizar via Git, siga este processo para aplicar as mudanças no serviço rodando.

### Processo Completo de Atualização

**1. Parar o serviço**

```cmd
nssm stop WhatsAppAgendadorBot
```

Ou, se estiver usando Método 3 (pywin32):
```cmd
python whatsapp_service.py stop
```

**2. Aplicar as atualizações**

**Opção A: Via Git (Recomendado)**

```cmd
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
git pull origin main
```

**Opção B: Edição Manual**

- Faça suas alterações nos arquivos `.py` usando seu editor
- Salve todas as mudanças
- Certifique-se de que não há erros de sintaxe

**Opção C: Aplicar Patch Específico**

Se você recebeu um arquivo `.patch`:

```cmd
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
git apply nome_do_patch.patch
```

**3. Atualizar dependências (se necessário)**

Se o `requirements.txt` foi modificado ou você adicionou novas bibliotecas:

```cmd
cd "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
pip install -r requirements.txt --upgrade
```

**4. Testar manualmente (RECOMENDADO)**

Antes de reiniciar o serviço, teste se o código está funcionando:

```cmd
python whatsapp_webhook.py
```

Verifique se:
- O servidor inicia sem erros
- Aparece a mensagem: `INFO:     Uvicorn running on http://0.0.0.0:8000`
- Não há exceções no console

Pressione `Ctrl+C` para parar o teste manual.

**5. Reiniciar o serviço**

```cmd
nssm start WhatsAppAgendadorBot
```

Ou, se estiver usando Método 3:
```cmd
python whatsapp_service.py start
```

**6. Verificar os logs**

```cmd
type "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\logs\service_output.log"
```

Procure por:
- `INFO:     Uvicorn running on http://0.0.0.0:8000` (servidor iniciou)
- `[startup] Slots inicializados com sucesso!` (slots carregaram)
- Sem linhas de `ERROR` ou `EXCEPTION`

### Script Rápido de Atualização

Crie um arquivo `atualizar_servico.bat` para automatizar o processo:

```batch
@echo off
echo ========================================
echo  ATUALIZANDO WHATSAPP BOT
echo ========================================
echo.

echo [1/6] Parando servico...
nssm stop WhatsAppAgendadorBot
timeout /t 3 /nobreak >nul

echo [2/6] Atualizando codigo via Git...
cd /d "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador"
git pull origin main

echo [3/6] Atualizando dependencias...
pip install -r requirements.txt --upgrade --quiet

echo [4/6] Testando codigo...
echo Pressione Ctrl+C se aparecer algum erro
timeout /t 2 /nobreak >nul
start /wait cmd /c "python whatsapp_webhook.py & timeout /t 5"

echo [5/6] Reiniciando servico...
nssm start WhatsAppAgendadorBot
timeout /t 2 /nobreak >nul

echo [6/6] Verificando logs...
nssm status WhatsAppAgendadorBot
echo.
echo Ultimas linhas do log:
powershell -Command "Get-Content 'logs\service_output.log' -Tail 10"

echo.
echo ========================================
echo  ATUALIZACAO CONCLUIDA!
echo ========================================
pause
```

Salve como: `c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador\atualizar_servico.bat`

Para usar, execute como **Administrador**.

### Rollback em Caso de Problemas

Se a atualização causou problemas, você pode reverter:

**Via Git:**

```cmd
# Ver commits recentes
git log --oneline -5

# Voltar para o commit anterior
git reset --hard HEAD~1

# Ou voltar para um commit específico
git reset --hard <hash-do-commit>

# Reiniciar o serviço
nssm restart WhatsAppAgendadorBot
```

**Backup Manual:**

Sempre mantenha um backup antes de atualizar:

```cmd
# Criar backup antes da atualização
xcopy "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador" "c:\Backups\ChatBot_%date%_%time:~0,2%%time:~3,2%" /E /I /H

# Para restaurar
xcopy "c:\Backups\ChatBot_<data>" "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador" /E /I /H /Y
```

### Atualizações Sem Downtime (Zero Downtime)

Para atualizações críticas sem parar o serviço:

1. **Clone o repositório em outra pasta**:
```cmd
git clone <url-repo> "c:\ChatBot_Staging"
cd c:\ChatBot_Staging
```

2. **Aplique e teste as mudanças na staging**:
```cmd
git checkout <branch-com-mudancas>
pip install -r requirements.txt
python whatsapp_webhook.py
```

3. **Se tudo OK, pare o serviço e copie os arquivos**:
```cmd
nssm stop WhatsAppAgendadorBot
xcopy "c:\ChatBot_Staging\*.py" "c:\Users\User\OneDrive - NORTETEL\Documentos\Miguel\Chat Bot Agendador" /Y
nssm start WhatsAppAgendadorBot
```

### Checklist de Atualização

Antes de atualizar, verifique:

- [ ] Você tem backup do código atual
- [ ] Você commitou todas as mudanças locais importantes
- [ ] Não há agendamentos críticos acontecendo no momento
- [ ] Você testou as mudanças em ambiente de desenvolvimento
- [ ] O `requirements.txt` está atualizado (se mudou dependências)

Após atualizar, verifique:

- [ ] O serviço iniciou sem erros
- [ ] Os logs não mostram exceções
- [ ] Uma mensagem de teste para o bot funciona
- [ ] O agendamento funciona normalmente
- [ ] Os schedulers diários estão rodando (`[daily_slots]`, `[reminder_check]`)

---

## Solução de Problemas

### Serviço não inicia

1. Verifique os logs em `logs\service_error.log`
2. Teste manualmente: `python whatsapp_webhook.py`
3. Verifique se todas as dependências estão instaladas
4. Confirme que o arquivo `.env` está no diretório correto

### Serviço inicia mas não responde

1. Verifique se a porta 8000 está livre: `netstat -ano | findstr :8000`
2. Verifique firewall do Windows
3. Confirme que o webhook do WhatsApp está apontando para o endereço correto

### Google Sheets não funciona

1. Verifique se `credentials.json` está no diretório
2. Se usando Local System account, mude para sua conta de usuário no NSSM
3. Execute manualmente uma vez para gerar `token.json`

### Scheduler não executa tarefas diárias

1. Verifique os logs: busque por `[daily_slots]` ou `[reminder_check]`
2. Confirme que o serviço está rodando continuamente
3. Teste manualmente as funções no código

---

## Monitoramento

Para monitorar o serviço em produção:

1. **Visualizador de Eventos** (Event Viewer):
   - Windows Logs > Application
   - Procure por eventos do serviço

2. **Logs do aplicativo**:
   - `logs\service_output.log`
   - `logs\service_error.log`

3. **Monitor de performance**:
   - Task Manager > Aba Serviços
   - Procure por "WhatsAppAgendadorBot"

---

## Próximos Passos Após Configurar

1. ✅ Teste enviar uma mensagem para o bot
2. ✅ Verifique se o agendamento funciona
3. ✅ Confirme que os lembretes são enviados no horário correto
4. ✅ Teste o scheduler de slots (aguarde até 00:01 ou force manualmente)
5. ✅ Configure backup automático do Google Sheets
6. ✅ Configure monitoramento de uptime (ex: UptimeRobot)
