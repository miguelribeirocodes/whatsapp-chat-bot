# 🎯 Próximas Etapas - Retomando o Webhook

**Status Atual:** ⏸️ Pausado - Aguardando acesso ao outro computador
**Data:** 2025-12-26
**Motivo da Pausa:** ngrok URL persistente sendo usada por outra instância

---

## 📋 O Que Aconteceu

### Problema Identificado
- Bot envia mensagens ✅ funcionando
- Bot NÃO recebe mensagens ❌ não funcionava
- Causa: ngrok URL `https://legalistic-unable-rob.ngrok-free.dev` está bloqueada por outra instância

### Mudanças Já Realizadas
1. ✅ Modificado `src/ngrok_service.py`:
   - Adicionado `override=True` ao `load_dotenv()` (linha 23)
   - Adicionado `bind_tls=True` ao `ngrok.connect()` (linha 80)

2. ✅ Criados scripts PowerShell:
   - `iniciar_servidor.ps1` - Inicia servidor SEM ngrok automático
   - `start_webhook.ps1` - Script alternativo

3. ✅ Documentação criada:
   - `SOLUCAO_WEBHOOK.md` - Explicação completa do problema
   - `PROBLEMA_NGROK_RESOLVIDO.md` - Root cause analysis
   - `GUIA_RAPIDO_WEBHOOK.md` - Quick reference

4. ✅ Mudanças no `.env`:
   - `NGROK_ENABLED=false` (temporariamente desabilitado)
   - `NGROK_AUTH_TOKEN` foi resetado (novo token no arquivo)

---

## 🚀 Quando Você Retornar (Próximo Dia)

### Passo 1: Parar a instância ngrok do outro computador
```powershell
# NO OUTRO COMPUTADOR
# Parar o servidor que está usando ngrok
taskkill /IM python.exe /F
taskkill /IM uvicorn.exe /F
```

### Passo 2: Limpar cache do ngrok
```powershell
# NESTE COMPUTADOR
# Remover configurações cached do ngrok
Remove-Item -Path "$env:USERPROFILE\.ngrok2" -Recurse -Force -ErrorAction SilentlyContinue
```

### Passo 3: Reabilitar ngrok
Edite o arquivo `.env` e mude:
```ini
# De:
NGROK_ENABLED=false

# Para:
NGROK_ENABLED=true
```

### Passo 4: Iniciar o servidor
```powershell
# Terminal PowerShell (na raiz do projeto)
.\iniciar_servidor.ps1
```

OU manualmente:
```powershell
.\.venv\Scripts\Activate.ps1
.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --reload --port 8000
```

### Passo 5: Capturar a nova URL do ngrok

Procure nos logs da saída do servidor por algo assim:
```
[ngrok] Tunnel established!
[ngrok] Public URL: https://XXXX-XXXX-XXXX.ngrok-free.dev
[ngrok] Webhook URL: https://XXXX-XXXX-XXXX.ngrok-free.dev/webhook
```

**Copie a URL completa do webhook** - você vai precisar dela no próximo passo.

### Passo 6: Configurar a URL no Meta for Developers

1. Acesse: https://developers.facebook.com/
2. Selecione seu app de WhatsApp
3. Vá para **Configurações > Configuração**
4. Em **Webhook URL**, cole a URL capturada no Passo 5
5. Em **Verify Token**, coloque:
   ```
   OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
   ```
6. Clique **Verificar e Salvar**

### Passo 7: Testar

Envie uma mensagem de teste via WhatsApp e confirme que:
- O servidor recebe a mensagem (logs mostram: `[webhook] Incoming POST payload`)
- O bot responde corretamente

---

## 🔄 Variáveis Importantes (Não Esqueça)

### .env Atual
```ini
WHATSAPP_TOKEN=EAASZB5ftnxCoBQTxbckCUt9sIB526dAGu6MgMEGQwFQDi0LG5LCqH4hEXj9xA4ZCyuYBZA8cdxSPtvyUegZAe4HteMgv35mMfFBnQi1QkEWuFfCbOOum3cMx94MqzznmYsUPhMCAIUo4w9mVlIY18QDu3XZBzwX6hElrFXxNe2rrCADD2DXtwmWsl1bX6TIuuovMr4ntqxd2pUQ55erScpCt9LZCYQjwYYIkEYfZCwKwdZBKl5bdaEQlMQs0zzVYRIKb6cY3k4G8yEpC3GHjzS6JFyy9
WHATSAPP_PHONE_ID=744785382061587
VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz

# Será ativado no Passo 3
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=37O33DJFQlfTH4ySRheZC2I7Hiw_bpSZh1HBR64vZmKdWFCb
NGROK_REGION=us
```

### URL Anterior (que estava bloqueada)
```
https://legalistic-unable-rob.ngrok-free.dev/webhook
```
**NÃO use esta URL** - ela está bloqueada pela outra instância.

---

## ✅ Checklist para Retomada

- [ ] Acessei o outro computador
- [ ] Parei os processos Python/uvicorn no outro computador
- [ ] Limpei o cache do ngrok: `Remove-Item -Path "$env:USERPROFILE\.ngrok2" -Recurse -Force`
- [ ] Mudei `NGROK_ENABLED=true` no `.env`
- [ ] Executei `.\iniciar_servidor.ps1`
- [ ] Capturei a nova URL do ngrok dos logs
- [ ] Configurei a nova URL no Meta for Developers
- [ ] Testei enviando uma mensagem via WhatsApp
- [ ] Bot respondeu corretamente ✅

---

## 📞 Logs Esperados (Verificação)

### Se tudo estiver funcionando:
```
[ngrok] Tunnel established!
[ngrok] Public URL: https://abc123def456.ngrok-free.dev
[ngrok] Webhook URL: https://abc123def456.ngrok-free.dev/webhook
INFO:     Uvicorn running on http://127.0.0.1:8000
[webhook] Incoming POST payload keys=...
```

### Se ngrok falhar:
```
[ngrok] Failed to start tunnel: The endpoint 'legalistic-unable-rob.ngrok-free.dev' is already online
```
⚠️ **Isso significa**: A outra instância ainda está rodando. Volte ao Passo 1.

### Se o webhook não receber mensagens:
1. Verifique se a URL está corretamente configurada no Meta for Developers
2. Teste a URL com curl:
   ```powershell
   curl "https://sua-url-aqui.ngrok-free.dev/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz"
   ```
   Deve retornar: `test`

---

## 📚 Documentação Relacionada

- [SOLUCAO_WEBHOOK.md](SOLUCAO_WEBHOOK.md) - Explicação completa do problema ngrok
- [PROBLEMA_NGROK_RESOLVIDO.md](PROBLEMA_NGROK_RESOLVIDO.md) - Análise técnica detalhada
- [GUIA_RAPIDO_WEBHOOK.md](GUIA_RAPIDO_WEBHOOK.md) - Quick reference para webhook
- [docs/CONFIGURAR_SERVICO_WINDOWS.md](docs/CONFIGURAR_SERVICO_WINDOWS.md) - Setup em produção
- [README.md](README.md) - Documentação principal

---

**Boa sorte! Quando retornar e conseguir acessar o outro computador, siga os passos acima em ordem.** 🚀
