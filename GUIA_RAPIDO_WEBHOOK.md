# 🚀 Guia Rápido: Configurar Webhook

## O Problema
O bot estava **enviando** mensagens, mas **não recebia** porque:
1. O ngrok não conseguiu gerar uma URL pública
2. O WhatsApp Cloud API não sabia para onde enviar as mensagens

## A Solução

### Passo 1: Iniciar o Servidor com URL Pública

```powershell
.\start_webhook.ps1
```

Aguarde até ver:
```
[ngrok] Webhook URL: https://xxxxxxxxxxxxx.ngrok-free.dev/webhook
```

**Copie essa URL** (você vai precisar nos próximos passos).

### Passo 2: Configurar no Meta for Developers

1. Acesse: https://developers.facebook.com/
2. Vá para sua app do WhatsApp
3. Selecione **Settings > Configuration**
4. Em **Webhook URL**, cole a URL do ngrok acima
5. Em **Verify Token**, use:
   ```
   OTljYjY3MWUtMmMxMy00MTM4LTk0MTQtYWM2MzI3MTRjZDUz
   ```
6. Clique em **Verify and Save**

### Passo 3: Testar

Envie uma mensagem para seu número de teste do WhatsApp. Agora o bot deve **receber** a mensagem!

## Por que isso funciona?

- **ngrok**: Cria um túnel entre seu computador local e a internet pública
- **VERIFY_TOKEN**: Autentica que o Meta está falando com o seu servidor
- **Webhook URL**: Endereço onde o Meta envia as mensagens do WhatsApp

## Se algo der errado

1. **"ngrok failed to start tunnel"**
   - Há outro ngrok/uvicorn rodando
   - Solução: Feche o script e execute novamente

2. **"Verification failed"**
   - Verify Token incorreto
   - Certifique-se de que os dois tokens coincidem

3. **Ainda não recebe mensagens**
   - Aguarde 2-3 minutos (pode levar para o Meta atualizar)
   - Verifique nos logs se há erros de conexão

## 📝 Notas

- A URL do ngrok **muda a cada execução** (é necessário atualizar no Meta cada vez)
- Para produção, use um domínio fixo em vez de ngrok
- O VERIFY_TOKEN foi atualizado no `.env` automaticamente

---
**Última atualização:** 2025-12-26
