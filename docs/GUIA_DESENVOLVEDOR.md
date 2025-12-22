# 📘 Guia do Desenvolvedor - Chat Bot Agendador

## 📋 Índice
1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Estrutura de Arquivos](#estrutura-de-arquivos)
3. [Fluxos Conversacionais](#fluxos-conversacionais)
4. [Como Fazer Modificações Comuns](#como-fazer-modificações-comuns)
5. [Sistema de Estados](#sistema-de-estados)
6. [Referência Rápida](#referência-rápida)

---

## 🏗️ Visão Geral da Arquitetura

O chatbot funciona como uma **máquina de estados** que processa mensagens do usuário e decide qual resposta enviar baseado no estado atual da conversa.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  WhatsApp   │────▶│   Webhook    │────▶│    Flow     │────▶│   Agenda     │
│   Cloud     │     │   (routing)  │     │  (lógica)   │     │  (Sheets)    │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                            │                     │                   │
                            ▼                     ▼                   ▼
                    ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
                    │  messages.py │     │constants.py │     │scheduler.py  │
                    │   (textos)   │     │ (constantes)│     │ (lembretes)  │
                    └──────────────┘     └─────────────┘     └──────────────┘
```

---

## 📁 Estrutura de Arquivos

### **Arquivos Principais** (os que você vai editar mais)

#### 1. **`messages.py`** - Textos do Bot
- **O que é:** Todas as mensagens que o bot envia ao usuário
- **Quando editar:** Quando quiser mudar textos, nome da clínica, horários de lembrete
- **Exemplos de edição:**
  ```python
  CLINIC_NAME = "Clínica X"  # Alterar nome da clínica
  MENU_AGENDAR = "Agendar"   # Alterar texto do botão
  REMINDER_HOURS_BEFORE = 24 # Enviar lembrete 24h antes
  ```

#### 2. **`whatsapp_flow.py`** - Lógica do Fluxo
- **O que é:** Toda a lógica conversacional (máquina de estados)
- **Quando editar:** Quando quiser adicionar novos fluxos ou modificar comportamento
- **Estrutura:**
  ```python
  def processar_mensagem(usuario_id, mensagem):
      estado = sessoes.get(usuario_id)  # Estado atual

      if estado == MENU_PRINCIPAL:
          # Lógica do menu principal

      if estado == AGENDAR:
          # Lógica de agendamento

      # ... outros estados
  ```

#### 3. **`whatsapp_webhook.py`** - Recebimento e Envio de Mensagens
- **O que é:** Recebe mensagens do WhatsApp e decide como responder
- **Quando editar:** Raramente (apenas se quiser adicionar novos tipos de botões)
- **Funções importantes:**
  - `send_text()` - Envia texto simples
  - `send_menu_buttons()` - Envia menu com botões
  - `send_list_days()` - Envia lista de dias
  - `send_confirm_buttons()` - Envia botões de confirmação

#### 4. **`constants.py`** - Constantes Centralizadas
- **O que é:** Todas as constantes usadas no código (IDs de botões, nomes de estados)
- **Quando editar:** Quando adicionar novos botões ou estados
- **Estrutura:**
  ```python
  # IDs de botões
  BUTTON_ID_AGENDAR = '1'
  BUTTON_ID_REAGENDAR = '2'

  # Estados do fluxo
  class States:
      MENU_PRINCIPAL = 'menu_principal'
      AGENDAR = 'agendar'

  # Chaves de sessão
  class SessionKeys:
      DIA_ESCOLHIDO = '_dia_escolhido'
  ```

#### 5. **`flow_helpers.py`** - Funções Auxiliares
- **O que é:** Funções reutilizáveis para formatação e manipulação
- **Quando editar:** Quando quiser mudar formatação de datas, horários, listas
- **Funções principais:**
  - `format_data_pt()` - Formata data em português
  - `format_appointment_list()` - Formata lista de agendamentos
  - `get_future_appointments()` - Busca agendamentos futuros

#### 6. **`agenda_service.py`** - Integração com Google Sheets
- **O que é:** Funções para ler/escrever na planilha
- **Quando editar:** Quando quiser mudar estrutura da planilha ou adicionar colunas
- **Funções principais:**
  - `registrar_agendamento_google_sheets()` - Salva agendamento
  - `cancelar_agendamento_por_data_hora()` - Cancela agendamento
  - `obter_todos_agenda_cached()` - Busca todos agendamentos

---

## 🔄 Fluxos Conversacionais

### **Fluxo 1: Agendamento Novo**

```
┌──────────────┐
│MENU_PRINCIPAL│ ← Usuário escolhe "Agendar"
└──────┬───────┘
       ▼
┌──────────────┐
│   AGENDAR    │ ← Usuário escolhe semana (Esta/Próxima)
└──────┬───────┘
       ▼
┌──────────────┐
│ESCOLHER_DIA  │ ← Usuário escolhe o dia
└──────┬───────┘
       ▼
┌──────────────┐
│ESCOLHER_HORA │ ← Usuário escolhe o horário
└──────┬───────┘
       ▼
┌──────────────┐
│  CONFIRMAR   │ ← Usuário confirma
└──────┬───────┘
       ▼
✅ Agendamento confirmado!
Volta ao MENU_PRINCIPAL
```

**Código correspondente em `whatsapp_flow.py`:**
- **MENU_PRINCIPAL:** Linhas 99-133
- **AGENDAR:** Linhas 138-167
- **ESCOLHER_DIA:** Linhas 279-309
- **ESCOLHER_HORARIO:** Linhas 314-348
- **CONFIRMAR:** Linhas 353-469

---

### **Fluxo 2: Reagendamento**

```
┌──────────────┐
│MENU_PRINCIPAL│ ← Usuário escolhe "Reagendar"
└──────┬───────┘
       ▼
┌──────────────┐
│  REAGENDAR   │ ← Sistema busca agendamentos futuros
└──────┬───────┘   e mostra lista
       ▼
Usuário escolhe qual agendamento reagendar
       ▼
┌──────────────┐
│   AGENDAR    │ ← Fluxo continua igual ao Fluxo 1
└──────────────┘   (escolher semana → dia → hora → confirmar)
```

**Código correspondente em `whatsapp_flow.py`:**
- **REAGENDAR:** Linhas 172-218
- Depois segue o fluxo normal de AGENDAR

**Diferença importante:** Quando confirma, o sistema automaticamente cancela o agendamento antigo antes de criar o novo (linha 374).

---

### **Fluxo 3: Cancelamento**

```
┌──────────────┐
│MENU_PRINCIPAL│ ← Usuário escolhe "Cancelar Agendamento"
└──────┬───────┘
       ▼
┌──────────────┐
│  CANCELAR    │ ← Sistema busca agendamentos futuros
└──────┬───────┘   e mostra lista
       ▼
Usuário escolhe qual agendamento cancelar
       ▼
┌──────────────────────────┐
│CONFIRM_CANCEL_APPOINTMENT│ ← Usuário confirma cancelamento
└──────────┬───────────────┘
           ▼
✅ Agendamento cancelado!
Volta ao MENU_PRINCIPAL
```

**Código correspondente em `whatsapp_flow.py`:**
- **CANCELAR:** Linhas 223-274
- **CONFIRM_CANCEL_APPOINTMENT:** Linhas 476-517

---

### **Fluxo 4: Consultar Valores**

```
┌──────────────┐
│MENU_PRINCIPAL│ ← Usuário escolhe "Valores e Pagamento"
└──────┬───────┘
       ▼
Mostra valores e formas de pagamento
       ▼
Volta ao MENU_PRINCIPAL (não muda estado)
```

**Código correspondente em `whatsapp_flow.py`:**
- **Linhas 126-128:** Apenas mostra informação e mantém no menu

---

## 🛠️ Como Fazer Modificações Comuns

### **1. Adicionar uma Nova Opção no Menu Principal**

**Passo 1:** Adicione o texto do botão em `messages.py`
```python
MENU_NOVA_OPCAO = "Nova Opção"
```

**Passo 2:** Adicione a constante do ID em `constants.py`
```python
BUTTON_ID_NOVA_OPCAO = '5'  # Próximo ID disponível
```

**Passo 3:** Adicione o estado em `constants.py` (se precisar de fluxo)
```python
class States:
    # ... estados existentes ...
    NOVA_OPCAO = 'nova_opcao'
```

**Passo 4:** Adicione o botão no menu em `flow_helpers.py` (linha 319)
```python
items = [
    (BUTTON_ID_AGENDAR, MSG.MENU_AGENDAR, ""),
    (BUTTON_ID_REAGENDAR, MSG.MENU_REAGENDAR, ""),
    (BUTTON_ID_CANCELAR, MSG.MENU_CANCELAR, ""),
    (BUTTON_ID_VALORES, MSG.MENU_VALORES, ""),
    (BUTTON_ID_NOVA_OPCAO, MSG.MENU_NOVA_OPCAO, ""),  # NOVA LINHA
]
```

**Passo 5:** Adicione a lógica em `whatsapp_flow.py` (após linha 128)
```python
# Opção 5: Nova Opção
elif mensagem == BUTTON_ID_NOVA_OPCAO:
    sessoes[usuario_id] = States.NOVA_OPCAO
    return "Mensagem inicial da nova opção"

# Adicione o estado também (após linha 517)
if estado == States.NOVA_OPCAO:
    # Sua lógica aqui
    if is_cancel:
        sessoes[usuario_id] = MENU_PRINCIPAL
        return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

    # ... resto da lógica
```

---

### **2. Mudar o Texto de uma Mensagem de Confirmação**

**Arquivo:** `messages.py` (linhas 50-72)

```python
# Exemplo: Mudar mensagem de agendamento confirmado
AGENDAMENTO_CONFIRMADO_FULL = """✅ Seu agendamento foi realizado!

📅 Data: {date}
🕐 Horário: {time}
👤 Nome: {name}

Aguardamos você! Até breve!"""
```

**⚠️ Importante:** Mantenha os placeholders `{date}`, `{time}`, `{name}` para que os dados sejam inseridos corretamente.

---

### **3. Alterar o Formato de Data/Hora**

**Arquivo:** `flow_helpers.py`

**Para mudar formato de data:**
```python
def format_data_pt(dt: Optional[date]) -> str:
    if dt is None:
        return ''
    weekday_name = NOMES_DIAS_PT[dt.weekday()]
    # Formato atual: "Segunda-feira, 23/12/2025"
    return f"{weekday_name}, {dt.day:02d}/{dt.month:02d}/{dt.year}"

    # Formato alternativo: "23/12/2025 (Segunda)"
    # return f"{dt.day:02d}/{dt.month:02d}/{dt.year} ({weekday_name})"
```

**Para mudar formato de hora:**
```python
def format_hora(dt: datetime) -> str:
    # Formato atual: "14:30"
    return dt.strftime('%H:%M')

    # Formato alternativo 12h: "02:30 PM"
    # return dt.strftime('%I:%M %p')
```

---

### **4. Adicionar um Campo Extra no Agendamento**

**Passo 1:** Adicione a coluna no Google Sheets manualmente

**Passo 2:** Atualize as constantes em `agenda_service.py`
```python
# Se adicionou coluna "Email" na posição 9 (coluna I)
AGENDA_EMAIL = 8  # índice 8 (coluna I)
```

**Passo 3:** Modifique a função `registrar_agendamento_google_sheets()` em `agenda_service.py`
```python
def registrar_agendamento_google_sheets(
    nome_paciente,
    data_hora_consulta,
    origem,
    telefone,
    observacoes="",
    email=""  # NOVO PARÂMETRO
):
    # ... código existente ...

    linha = [
        nome_paciente,
        data_str,
        hora_str,
        nome_paciente,
        telefone,
        "AGENDADO",
        observacoes,
        origem,
        email  # NOVA COLUNA
    ]
```

**Passo 4:** Adicione lógica para perguntar o email no fluxo (em `whatsapp_flow.py`)

---

### **5. Mudar Horário do Resumo Diário para o Dono**

**Arquivo:** `messages.py` (linha 100)

```python
# Horário atual: 7h da manhã
OWNER_DAILY_SUMMARY_HOUR = 7

# Para mudar para 8h:
OWNER_DAILY_SUMMARY_HOUR = 8

# Para mudar para 18h (6 da tarde):
OWNER_DAILY_SUMMARY_HOUR = 18
```

---

### **6. Mudar Quando o Lembrete é Enviado**

**Arquivo:** `messages.py` (linha 91)

```python
# Lembrete atual: 24 horas antes
REMINDER_HOURS_BEFORE = 24

# Para enviar 48 horas antes:
REMINDER_HOURS_BEFORE = 48

# Para enviar 1 hora antes:
REMINDER_HOURS_BEFORE = 1
```

---

## 🎯 Sistema de Estados

### **Como Funciona**

O bot mantém um dicionário `sessoes` que guarda o estado de cada usuário:

```python
sessoes = {
    '5538991234567': 'escolher_dia',           # Estado atual do usuário
    '5538991234567_dia_escolhido': date(2025, 12, 25),  # Dia escolhido
    '5538991234567_horario_escolhido': datetime(...),   # Horário escolhido
}
```

### **Estados Disponíveis**

| Estado | Descrição | Arquivo | Linhas |
|--------|-----------|---------|--------|
| `MENU_PRINCIPAL` | Menu inicial | whatsapp_flow.py | 99-133 |
| `AGENDAR` | Escolher semana | whatsapp_flow.py | 138-167 |
| `ESCOLHER_DIA` | Escolher dia | whatsapp_flow.py | 279-309 |
| `ESCOLHER_HORARIO` | Escolher horário | whatsapp_flow.py | 314-348 |
| `CONFIRMAR` | Confirmar agendamento | whatsapp_flow.py | 353-469 |
| `REAGENDAR` | Listar agendamentos para reagendar | whatsapp_flow.py | 172-218 |
| `CANCELAR` | Listar agendamentos para cancelar | whatsapp_flow.py | 223-274 |
| `CONFIRM_CANCEL_APPOINTMENT` | Confirmar cancelamento | whatsapp_flow.py | 476-517 |

### **Transições de Estado**

**Exemplo prático:**

```python
# Usuário está no menu e escolhe "Agendar"
if estado == MENU_PRINCIPAL:
    if mensagem == BUTTON_ID_AGENDAR:
        sessoes[usuario_id] = AGENDAR  # ← Muda estado
        return exibir_semanas_disponiveis(usuario_id)

# Agora o usuário está em AGENDAR e escolhe "Esta semana"
if estado == AGENDAR:
    if mensagem == BUTTON_ID_ESTA_SEMANA:
        sessoes[usuario_id] = ESCOLHER_DIA  # ← Muda estado novamente
        return exibir_dias_disponiveis(usuario_id, 0)
```

---

## 📚 Referência Rápida

### **Onde Encontrar Cada Coisa**

| O que você quer fazer | Arquivo | Linhas |
|----------------------|---------|--------|
| Mudar texto do menu | messages.py | 15-21 |
| Mudar mensagens de confirmação | messages.py | 50-72 |
| Mudar horário de lembrete | messages.py | 91 |
| Mudar horário do resumo diário | messages.py | 100 |
| Adicionar botão no menu | flow_helpers.py | 319-324 |
| Modificar fluxo de agendamento | whatsapp_flow.py | 138-469 |
| Modificar fluxo de reagendamento | whatsapp_flow.py | 172-218 |
| Modificar fluxo de cancelamento | whatsapp_flow.py | 223-274 |
| Mudar formato de data | flow_helpers.py | 15-23 |
| Mudar formato de hora | flow_helpers.py | 26-31 |
| Adicionar novo botão (ID) | constants.py | 15-28 |
| Adicionar novo estado | constants.py | 34-50 |
| Funções do Google Sheets | agenda_service.py | - |

### **IDs de Botões Padrão**

```python
'1' = Agendar / Confirmar / Esta semana
'2' = Reagendar / Próxima semana
'3' = Cancelar Agendamento
'4' = Valores e Pagamento
'0' = Voltar
'9' = Cancelar Operação
```

### **Mensagens Especiais para Detecção**

O webhook detecta automaticamente estas mensagens e envia botões apropriados:

| Mensagem contém | Tipo de botões enviados |
|----------------|------------------------|
| `"Sou a secretária virtual"` + `"Selecione uma opção"` | Menu principal |
| `"semana"` + `"escolh"` | Botões de semana |
| `"dia"` + `"escolh"` | Lista de dias |
| `"horár"` + `"escolh"` | Lista de horários |
| `"confirma"` | Botões de confirmação |
| `"✅"` + `"confirmado"` | Texto + Menu (separados) |

---

## 🚀 Exemplo Completo: Adicionar Campo "Observações" no Agendamento

### **Cenário:**
Você quer que o usuário possa adicionar uma observação opcional antes de confirmar o agendamento.

### **Implementação:**

**1. Adicione estado em `constants.py`:**
```python
class States:
    # ... estados existentes ...
    PEDIR_OBSERVACAO = 'pedir_observacao'
```

**2. Adicione chave de sessão em `constants.py`:**
```python
class SessionKeys:
    # ... chaves existentes ...
    OBSERVACAO = '_observacao'
```

**3. Modifique `whatsapp_flow.py` - Estado ESCOLHER_HORARIO (linha 335):**
```python
if is_valid_selection(horario_idx, horarios):
    sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.HORARIO_ESCOLHIDO)] = horarios[horario_idx]
    # Ao invés de ir direto para CONFIRMAR, pergunta observação
    sessoes[usuario_id] = PEDIR_OBSERVACAO
    return "Deseja adicionar alguma observação? (Digite ou envie '0' para pular)"
```

**4. Adicione novo estado em `whatsapp_flow.py` (após linha 348):**
```python
# ========================================================================
# ESTADO: PEDIR_OBSERVACAO
# ========================================================================
if estado == States.PEDIR_OBSERVACAO:
    if is_cancel:
        sessoes[usuario_id] = MENU_PRINCIPAL
        cleanup_agendamento_session(sessoes, usuario_id)
        return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

    if is_back or mensagem == '0':
        # Pular observação
        sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.OBSERVACAO)] = ""
    else:
        # Salvar observação
        sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.OBSERVACAO)] = mensagem

    # Ir para confirmação
    sessoes[usuario_id] = CONFIRMAR
    horario = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.HORARIO_ESCOLHIDO))
    return MSG.CONFIRM_AGENDAMENTO_TEMPLATE.format(
        date=format_data_pt(horario),
        time=horario.strftime('%H:%M')
    )
```

**5. Modifique `whatsapp_flow.py` - Estado CONFIRMAR (linha 378):**
```python
# Pegar observação da sessão
observacao = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.OBSERVACAO), "")

# Registrar novo agendamento
registrar_agendamento_google_sheets(
    nome_paciente=nome_paciente,
    data_hora_consulta=horario,
    origem="whatsapp_simulado",
    telefone=usuario_id,
    observacoes=observacao  # ← Passar observação aqui
)
```

**6. Limpe a observação no cleanup em `flow_helpers.py` (linha 197):**
```python
def cleanup_agendamento_session(sessoes: dict, usuario_id: str):
    cleanup_session_keys(sessoes, usuario_id, [
        '_semana_offset',
        '_dia_escolhido',
        '_horario_escolhido',
        '_reagendar_antigo',
        '_observacao'  # ← ADICIONAR AQUI
    ])
```

Pronto! Agora o fluxo pede observação antes de confirmar.

---

## ⚠️ Avisos Importantes

### **Cuidados ao Editar**

1. **NUNCA remova os placeholders** `{date}`, `{time}`, `{name}` das mensagens em `messages.py`
2. **SEMPRE teste** após fazer modificações no fluxo conversacional
3. **Mantenha consistência** entre IDs de botões em `constants.py` e uso em `whatsapp_flow.py`
4. **Use SessionKeys** ao invés de strings hardcoded para chaves de sessão
5. **Use helpers** de `flow_helpers.py` ao invés de duplicar código

### **Testando Modificações**

Para testar localmente sem WhatsApp:
```bash
python whatsapp_flow.py
```

Isso abre um simulador de conversa no terminal.

---

## 📞 Estrutura de Resposta do WhatsApp

### **Como o Webhook Decide o Tipo de Resposta**

O arquivo `whatsapp_webhook.py` (linhas 621-735) analisa a resposta do fluxo e decide qual função chamar:

```python
if has_menu and has_confirmation:
    # Envia confirmação + menu separadamente
    send_text(confirmation_part)
    send_menu_buttons(menu_text, menu_items)

elif menu_text in resposta:
    # Envia menu com botões interativos
    send_menu_buttons(resposta, menu_items)

elif 'semana' in resposta and 'escolh' in resposta:
    # Envia botões de semana
    send_weeks_buttons(MSG.WEEKS_PROMPT)

elif 'dia' in resposta and 'escolh' in resposta:
    # Envia lista de dias
    send_list_days(title, items)

elif 'confirma' in resposta:
    # Envia botões de confirmação
    send_confirm_buttons(resposta)

else:
    # Envia texto simples
    send_text(resposta)
```

**Dica:** Se adicionar novo tipo de interação, adicione detecção aqui!

---

## 🎓 Recursos Adicionais

- **Documentação WhatsApp Cloud API:** https://developers.facebook.com/docs/whatsapp/cloud-api
- **Google Sheets API:** https://developers.google.com/sheets/api
- **FastAPI:** https://fastapi.tiangolo.com/

---

**Criado em:** 18/12/2025
**Última atualização:** 18/12/2025
**Versão:** 1.0
