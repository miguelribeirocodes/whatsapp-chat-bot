# 🔴 Sistema de Notificações de Erro para Desenvolvedor

## Overview

Sistema automático que notifica o desenvolvedor via WhatsApp quando erros críticos ocorrem no bot. Útil para debugar problemas em produção sem acesso direto aos logs do servidor.

## Configuração

### 1. Definir DEV_PHONE em messages.py

```python
# src/messages.py

# Telefone do desenvolvedor para notificações de erro (mesmo formato internacional)
# Se deixado vazio, desabilita notificações de erro por WhatsApp
DEV_PHONE = "553899135151"  # ← Mude para seu número
```

**Formato:** Número internacional sem espaços ou caracteres especiais
- ✅ Correto: `553899135151`
- ❌ Incorreto: `+55 (38) 99135151`

### 2. Para desabilitar notificações

Deixe a variável vazia:

```python
DEV_PHONE = ""  # Notificações desabilitadas
```

## Uso

### Exemplo 1: Notificar erro em uma função

```python
from src import whatsapp_webhook

try:
    resultado = fazer_algo_critico()
except Exception as e:
    whatsapp_webhook.notify_dev_error(
        error_msg=f"Erro ao processar paciente: {str(e)}",
        context="agenda_service.obter_slots"
    )
```

### Exemplo 2: Notificar erro de API

```python
if response.status_code != 200:
    whatsapp_webhook.notify_dev_error(
        error_msg=f"WhatsApp API erro {response.status_code}: {response.text[:200]}",
        context="send_list_days"
    )
```

### Exemplo 3: Em agenda_service.py (evitar circular imports)

```python
try:
    registros = ws.get_all_records()
except Exception as e:
    _notify_dev_error_safe(
        error_msg=f"Erro ao ler Google Sheets: {str(e)}",
        context="obter_slots_disponiveis_para_data"
    )
```

## Função: `notify_dev_error()`

**Localização:** `src/whatsapp_webhook.py:101-123`

**Assinatura:**
```python
def notify_dev_error(error_msg: str, context: str = ""):
    """
    Envia notificação de erro para o DEV_PHONE configurado em messages.py

    Args:
        error_msg: Mensagem de erro a enviar (string ou exceção)
        context: Contexto adicional (ex: nome da função, user_id, etc)
    """
```

**Exemplo de mensagem recebida:**

```
🔴 ERRO [send_list_days] 04/01/2026 07:52:07

Status 400 ao enviar lista para 553899135151
Título: Escolha o dia
Rows: 11
Resposta: {"error":{"message":"(#131009) Parameter value is not valid"...
```

## Locais Onde Já Foi Integrado

1. ✅ **send_list_days()** - Erros ao enviar listas interativas
   - Status != 200 → notificação imediata
   - Exceção → notificação com traceback

2. 🔜 **send_text()** - Pode ser adicionado para erros de envio de texto

3. 🔜 **agenda_service.py** - Erros ao acessar Google Sheets

4. 🔜 **scheduler.py** - Erros ao executar tasks agendadas

## Boas Práticas

### ✅ Fazer

```python
# Mensagem clara e concisa
notify_dev_error("Token expirado ao enviar para 553899135151", "send_text")

# Com contexto de usuário/dados
notify_dev_error(f"Erro ao agendar para user {user_id}: {str(e)}", "confirmar_agendamento")

# Truncar mensagens muito longas
notify_dev_error(f"Resposta API: {response.text[:200]}...", "graph_api")
```

### ❌ Evitar

```python
# Não notificar para erros simples/esperados
if user_input == "inválido":
    # Não chamar notify_dev_error - isso é tratamento normal
    send_text(user, "Opção inválida")

# Não enviar informações sensíveis
notify_dev_error(f"Token do usuário: {token}", ...)  # NUNCA!

# Não notificar muitas vezes seguidas (spam)
for item in items:
    try:
        processar(item)
    except:
        notify_dev_error(...)  # Pode gerar 100 mensagens
```

## Tratamento de Erros

Se a notificação falhar (ex: DEV_PHONE inválido, sem internet), o sistema:
1. Loga o erro localmente
2. **Não quebra a execução** do bot
3. **Não relança a exceção**

```python
def notify_dev_error(error_msg: str, context: str = ""):
    try:
        # ... enviar mensagem
    except Exception as e:
        logger.error("[notify_dev_error] Falha ao enviar: %s", str(e))
        # Não relança - previne cascata de erros
```

## Funcionalidade Helper: `_notify_dev_error_safe()`

**Localização:** `src/agenda_service.py:19-25`

Use quando importar `whatsapp_webhook` for circular ou inseguro:

```python
# Em agenda_service.py
from src.agenda_service import _notify_dev_error_safe

try:
    resultado = algo()
except Exception as e:
    _notify_dev_error_safe(str(e), "minha_funcao")
```

**Protege contra:**
- Circular imports
- Exceções na importação
- DEV_PHONE não configurado

## Monitoramento

Para ver todas as notificações de erro enviadas, procure nos logs:

```bash
# No servidor
grep "notify_dev_error\|Enviando notificação de erro" ~/whatsapp-chat-bot/logs/app.log

# Últimas 20 notificações
grep "notify_dev_error" ~/whatsapp-chat-bot/logs/app.log | tail -20
```

## Desabilitação Temporária

Para desabilitar durante testes sem remover o código:

```python
# Em messages.py
DEV_PHONE = ""  # Vazio = desabilitado
```

## Futuros Melhoramentos

- [ ] Incluir screenshot/context da conversa que causou erro
- [ ] Rate limiting para evitar spam (máx 1 msg/min por tipo)
- [ ] Dashboard web de erros
- [ ] Histórico de erros no Sheets

---

**Versão:** 1.0
**Data:** 04/01/2026
**Autor:** Claude Code
