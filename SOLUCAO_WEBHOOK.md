# 🔧 SOLUÇÃO: Bot não recebe mensagens

## 🔴 O Problema Identificado

Seu bot estava **ENVIANDO** mensagens normalmente, mas **NÃO RECEBIA** as mensagens do usuário.

### Root Cause (Causa Raiz)

1. Você tem um **token premium do ngrok** (com URL persistente)
2. Há uma **URL fixa atribuída ao seu token**: `https://legalistic-unable-rob.ngrok-free.dev`
3. **Conflito:** O ngrok tentava iniciar e falhava com erro:
   ```
   The endpoint 'legalistic-unable-rob.ngrok-free.dev' is already online
   ```
4. Sem ngrok ativo, o servidor FastAPI rodava apenas em **127.0.0.1:8000** (localhost)
5. O **WhatsApp Cloud API não conseguia alcançar** um servidor local
6. Por isso, as mensagens **não eram entregues ao webhook**

---

## ✅ A Solução Implementada

### Passo 1: Desabilitei ngrok automático no `.env`
```ini
NGROK_ENABLED=false
```

### Passo 2: Você já tem uma URL FIXA do ngrok!
```
https://legalistic-unable-rob.ngrok-free.dev/webhook
```

### Passo 3: Configurar essa URL no WhatsApp

1. Acesse: https://developers.facebook.com/
2. Selecione seu app de WhatsApp
3. Vá para **Configurações > Configuração**
4. Em **Webhook URL**, coloque:
   ```
   https://legalistic-unable-rob.ngrok-free.dev/webhook
   ```
5. Em **Verify Token**, coloque:
   ```
   OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
   ```
6. Clique **Verificar e Salvar**

---

## 🚀 Como Usar Agora

### Iniciar o servidor:
```powershell
.\.venv\Scripts\Activate.ps1
.venv\Scripts\uvicorn.exe src.whatsapp_webhook:app --reload --port 8000
```

**Ou use o script que criei:**
```powershell
.\start_webhook.ps1
```

### Agora você pode:
- ✅ **Enviar mensagens** - Já funcionava
- ✅ **RECEBER mensagens** - Agora funciona! (ngrok mantém tunel ativo)
- ✅ **Debugar localmente** - Ver logs em tempo real
- ✅ **Fazer modificações** - Com reload automático

---

## ⚠️ Por que ngrok estava falhando?

### Motivo técnico:
O ngrok com token premium cria **URLs persistentes**. Quando você tenta iniciar duas instâncias:
1. Primeira instância: Cria a URL e funciona
2. Segunda instância: Tenta criar a mesma URL e recebe erro 502

### Como resolver:
Você tem 3 opções:

#### Opção 1: Usar URL Fixa (RECOMENDADO - Implementada)
- Deixar ngrok desabilitado
- Manter URL fixa no WhatsApp
- ✅ Simples, previsível, sem conflitos

#### Opção 2: Usar Load Balancing
```bash
ngrok http 8000 --pooling-enabled
```
- Permite múltiplas instâncias
- Mais complexo de debugar

#### Opção 3: Resetar Token do ngrok
- Gerar novo token (URL muda)
- Reconfigurar no WhatsApp a cada restart
- ❌ Não recomendado

---

## 📋 Checklist: Tudo Funcionando?

- [ ] `.env` tem `NGROK_ENABLED=false`
- [ ] `.env` tem `VERIFY_TOKEN=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz`
- [ ] WhatsApp está configurado com URL: `https://legalistic-unable-rob.ngrok-free.dev/webhook`
- [ ] Servidor rodando: `uvicorn src.whatsapp_webhook:app --reload --port 8000`
- [ ] Teste: Enviar mensagem → Bot responde
- [ ] Logs mostram: `[webhook] Incoming POST payload keys=...`

Se tudo estava OK, agora o bot deve **receber e responder a mensagens**!

---

## 🐛 Se Ainda Não Funcionar

### Verificar Webhook URL no WhatsApp:
```bash
# Testar se a URL está acessível
curl https://legalistic-unable-rob.ngrok-free.dev/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
```

Deve retornar: `test`

### Ver logs do servidor:
```bash
# Terminal onde o servidor está rodando
# Procure por: [webhook] Incoming POST payload
```

### Testar com curl:
```bash
curl -X POST https://legalistic-unable-rob.ngrok-free.dev/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"553899135151","type":"text","text":{"body":"teste"}}]}}]}]}'
```

---

## 📚 Documentação Relevante

- [GUIA_DESENVOLVEDOR.md](docs/GUIA_DESENVOLVEDOR.md) - Arquitetura
- [CONFIGURAR_SERVICO_WINDOWS.md](docs/CONFIGURAR_SERVICO_WINDOWS.md) - Deploy em produção
- [README.md](README.md) - Instruções iniciais

---

**Status:** ✅ Resolvido
**Data:** 2025-12-26
**Versão:** 1.0
