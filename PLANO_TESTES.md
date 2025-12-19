# 📋 Plano de Testes - Chat Bot Agendador

**Data:** 18/12/2025
**Versão:** 1.0 - Pós-refatoração completa

---

## 🎯 Objetivo

Validar todas as funcionalidades do bot após as refatorações e implementações de:
- Sistema de slots com janela deslizante (30 dias)
- Mensagens de confirmação melhoradas
- Notificações ao dono (agendamento, cancelamento, reagendamento)
- Fluxos refatorados (menu, agendamento, reagendamento, cancelamento)

---

## 📱 Pré-requisitos

1. ✅ Bot rodando e conectado ao WhatsApp Cloud API
2. ✅ Google Sheets acessível e com permissões corretas
3. ✅ Variável `CLINIC_OWNER_PHONE` configurada em `messages.py`
4. ✅ Ter acesso ao telefone do dono para validar notificações
5. ✅ Planilha Google Sheets limpa ou com dados de teste

---

## 🧪 Testes de Funcionalidades Principais

### **TESTE 1: Inicialização do Bot**

**Objetivo:** Verificar se os slots são gerados automaticamente ao iniciar o bot.

**Passos:**
1. Reiniciar o bot (parar e iniciar novamente)
2. Verificar os logs do terminal/console

**Resultado Esperado:**
```
[startup] Inicializando slots para os próximos 30 dias...
[startup] Slots inicializados com sucesso!
```

**Validação:**
- Abrir Google Sheets → Aba "Agenda"
- Verificar se existem slots com status "DISPONIVEL" para os próximos 30 dias úteis (seg-sex)
- Verificar formato: `dia_semana | data | hora | "" | "" | DISPONIVEL | "" | ""`

**Critério de Sucesso:** ✅ Slots criados para 30 dias úteis

---

### **TESTE 2: Primeiro Contato (Cadastro Novo)**

**Objetivo:** Validar fluxo de cadastro de novo usuário.

**Passos:**
1. Enviar mensagem do WhatsApp de um número **NOVO** (não cadastrado)
2. Aguardar resposta do bot

**Resultado Esperado:**
```
Olá! Por favor, informe seu nome completo:
```

**Passos (continuação):**
3. Responder com: `Miguel Silva`
4. Aguardar resposta

**Resultado Esperado:**
- Mensagem de saudação: `Olá, Miguel!`
- Menu principal com 4 opções:
  - Agendar
  - Reagendar
  - Cancelar Agendamento
  - Valores e Pagamento

**Validação:**
- Abrir Google Sheets → Aba "Cadastros"
- Verificar se apareceu nova linha com: telefone, nome "Miguel Silva", data/hora de cadastro, origem "whatsapp_cloud"

**Critério de Sucesso:** ✅ Cadastro criado e menu exibido

---

### **TESTE 3: Usuário Já Cadastrado**

**Objetivo:** Validar que usuário cadastrado vai direto ao menu.

**Passos:**
1. Com o mesmo número do TESTE 2, enviar qualquer mensagem (ex: "Oi")

**Resultado Esperado:**
- Saudação personalizada: `Olá, Miguel!`
- Menu principal com botões interativos

**Resultado real:**
- Olá! Seja bem-vindo(a)!
- Olá, Miguel!
Sou a secretária virtual da Clínica X.
Selecione uma opção
- Obs.: eu esperava que não viesse a primeira mensagem "Bem-vindo(a)"

**Critério de Sucesso:** ✅ Menu exibido imediatamente sem pedir nome

---

### **TESTE 4: Fluxo de Agendamento Completo**

**Objetivo:** Validar fluxo completo de novo agendamento.

**Passos:**
1. No menu principal, clicar em "Agendar"
2. Aguardar mensagem

**Resultado Esperado:**
```
Escolha a semana:
- Esta semana
- Próxima semana
- Cancelar
```

**Passos (continuação):**
3. Clicar em "Esta semana"
4. Aguardar lista de dias

**Resultado Esperado:**
- Lista interativa de dias disponíveis da semana atual
- Formato: "Segunda-feira, 23/12/2025" (ou similar)
- Opções "Voltar" e "Cancelar" na lista

**Passos (continuação):**
5. Escolher um dia (ex: primeiro da lista)
6. Aguardar mensagem "Aguarde um momento, por favor."
7. Aguardar lista de horários

**Resultado Esperado:**
- Lista interativa de horários disponíveis (ex: 08:00, 08:50, 09:40, etc.)
- Opções "Voltar" e "Cancelar"

**Passos (continuação):**
8. Escolher um horário (ex: 14:00)
9. Aguardar confirmação

**Resultado Esperado:**
```
Confirma o agendamento para Segunda-feira, 23/12/2025 às 14:00?
- Confirmar
- Voltar
- Cancelar
```

**Passos (continuação):**
10. Clicar em "Confirmar"

**Resultado Esperado - Mensagem ao Paciente:**
```
✅ Agendamento *confirmado* com sucesso!

📅 Data: Segunda-feira, 23/12/2025
🕐 Horário: 14:00

Você receberá um lembrete 24 horas antes da consulta.
Até lá!
```

Seguido do menu principal novamente.

**Resultado Esperado - Notificação ao Dono:**
O telefone do dono (configurado em `CLINIC_OWNER_PHONE`) deve receber:
```
📅 *NOVO AGENDAMENTO*

👤 Paciente: Miguel
📆 Data: 23/12/2025
🕐 Horário: 14:00

Agendamento confirmado pelo WhatsApp.
```

**Validação - Google Sheets:**
- Aba "Agenda": Verificar linha do slot escolhido
  - Status mudou para "AGENDADO"
  - Nome do paciente preenchido: "Miguel Silva"
  - Telefone preenchido
  - Origem: "whatsapp_simulado"

- Aba "Lembretes": Verificar se foi criado lembrete
  - `scheduled_iso`: data/hora 24h antes do agendamento
  - `appointment_iso`: data/hora do agendamento
  - `telefone`: número do paciente
  - `paciente`: "Miguel Silva"
  - `sent_at`: vazio (ainda não enviado)

**Critério de Sucesso:**
- ✅ Mensagem de confirmação exibida ao paciente
- ✅ Notificação enviada ao dono
- ✅ Slot marcado como AGENDADO no Sheets
- ✅ Lembrete criado na aba Lembretes

---

### **TESTE 5: Fluxo de Reagendamento Completo**

**Objetivo:** Validar reagendamento e notificação especial ao dono.

**Pré-requisito:** Ter pelo menos um agendamento futuro (criado no TESTE 4).

**Passos:**
1. No menu principal, clicar em "Reagendar"
2. Aguardar lista de agendamentos

**Resultado Esperado:**
```
Escolha o agendamento para reagendar:
1️⃣ Segunda-feira, 23/12/2025 14:00 - Miguel
⬅️ Voltar
```

**Passos (continuação):**
3. Clicar no agendamento (opção 1)
4. Escolher "Esta semana" ou "Próxima semana"
5. Escolher um DIA diferente do agendamento atual
6. Escolher um HORÁRIO diferente
7. Confirmar

**Resultado Esperado - Mensagem ao Paciente:**
```
✅ Reagendamento *realizado* com sucesso!

📅 Nova data: Quarta-feira, 25/12/2025
🕐 Novo horário: 15:00

O agendamento anterior foi cancelado.
Você receberá um lembrete 24 horas antes da consulta.
```

**Resultado Esperado - Notificação ao Dono:**
```
🔄 *REAGENDAMENTO*

👤 Paciente: Miguel
📆 Data anterior: 23/12/2025
🕐 Horário anterior: 14:00

📆 Nova data: 25/12/2025
🕐 Novo horário: 15:00

O agendamento anterior foi cancelado automaticamente.
```

**Validação - Google Sheets:**
- Aba "Agenda":
  - Slot antigo (23/12 14:00) deve estar DISPONIVEL novamente (limpo)
  - Slot novo (25/12 15:00) deve estar AGENDADO com dados do paciente

- Aba "Lembretes":
  - Lembrete antigo deve ter sido removido
  - Novo lembrete criado para o novo agendamento

**Critério de Sucesso:**
- ✅ Mensagem específica de reagendamento ao paciente
- ✅ Notificação única ao dono com dados antigos E novos
- ✅ Slot antigo liberado
- ✅ Novo slot agendado

---

### **TESTE 6: Fluxo de Cancelamento Completo**

**Objetivo:** Validar cancelamento e notificação ao dono.

**Pré-requisito:** Ter pelo menos um agendamento futuro.

**Passos:**
1. No menu principal, clicar em "Cancelar Agendamento"
2. Aguardar lista de agendamentos

**Resultado Esperado:**
```
Escolha o agendamento para cancelar:
1️⃣ Quarta-feira, 25/12/2025 15:00 - Miguel
⬅️ Voltar
```

**Passos (continuação):**
3. Clicar no agendamento
4. Aguardar confirmação

**Resultado Esperado:**
```
Confirma o cancelamento do agendamento em Quarta-feira, 25/12/2025 às 15:00?
- Confirmar
- Voltar
- Cancelar
```

**Passos (continuação):**
5. Clicar em "Confirmar"

**Resultado Esperado - Mensagem ao Paciente:**
```
✅ Agendamento *cancelado* com sucesso!

📅 Data: Quarta-feira, 25/12/2025
🕐 Horário: 15:00

Se precisar reagendar, estou à disposição!
```

**Resultado Esperado - Notificação ao Dono:**
```
❌ *CANCELAMENTO*

👤 Paciente: Miguel
📆 Data: 25/12/2025
🕐 Horário: 15:00

Agendamento cancelado pelo WhatsApp.
```

**Validação - Google Sheets:**
- Aba "Agenda": Slot deve estar DISPONIVEL novamente
- Aba "Lembretes": Lembrete deve ter sido removido

**Critério de Sucesso:**
- ✅ Mensagem de cancelamento ao paciente
- ✅ Notificação ao dono
- ✅ Slot liberado

---

### **TESTE 7: Opção "Valores e Pagamento"**

**Objetivo:** Validar exibição de informações de pagamento.

**Passos:**
1. No menu principal, clicar em "Valores e Pagamento"

**Resultado Esperado:**
```
Valores e Formas de Pagamento

Consulta: R$ 150,00. Aceitamos: Cartão, Pix e Dinheiro. O pagamento será realizado no momento da consulta.
```

Com botão "Voltar" que retorna ao menu.

**Critério de Sucesso:** ✅ Informação exibida e botão Voltar funciona

---

### **TESTE 8: Cancelar Operação (Botão Cancelar)**

**Objetivo:** Validar que usuário pode cancelar operação a qualquer momento.

**Passos:**
1. Iniciar fluxo de agendamento (clicar em "Agendar")
2. Escolher "Esta semana"
3. Na lista de dias, clicar em "Cancelar"

**Resultado Esperado:**
```
Operação cancelada.
```

Seguido do menu principal.

**Critério de Sucesso:** ✅ Volta ao menu sem fazer agendamento

---

### **TESTE 9: Botão Voltar**

**Objetivo:** Validar navegação para trás no fluxo.

**Passos:**
1. Clicar em "Agendar"
2. Escolher "Esta semana"
3. Na lista de dias, clicar em "Voltar"

**Resultado Esperado:**
- Volta para seleção de semana (Esta semana / Próxima semana)

**Passos (continuação):**
4. Escolher "Esta semana" novamente
5. Escolher um dia
6. Na lista de horários, clicar em "Voltar"

**Resultado Esperado:**
- Volta para lista de dias

**Critério de Sucesso:** ✅ Navegação para trás funciona em todos os níveis

---

### **TESTE 10: Slot com Status FOLGA**

**Objetivo:** Validar que slots marcados como FOLGA não são listados e não são sobrescritos.

**Passos:**
1. Abrir Google Sheets → Aba "Agenda"
2. Manualmente, mudar um slot de "DISPONIVEL" para "FOLGA" (ex: 26/12/2025 09:00)
3. No bot, iniciar agendamento para essa data

**Resultado Esperado:**
- Ao listar horários do dia 26/12, o horário 09:00 NÃO deve aparecer na lista
- Apenas horários com status DISPONIVEL aparecem

**Validação Adicional:**
4. Aguardar até meia-noite (ou simular mudança de data no sistema)
5. Verificar nos logs se o scheduler rodou:
```
[daily_slots] Slot 26/12/2025 09:00 tem status FOLGA, mantendo
```

**Critério de Sucesso:**
- ✅ Slots com FOLGA não aparecem nas listagens
- ✅ Sistema não sobrescreve FOLGA

---

## 🤖 Testes de Sistema e Schedulers

### **TESTE 11: Scheduler Diário de Slots (Janela Deslizante)**

**Objetivo:** Validar que slots são adicionados diariamente.

**Configuração:**
- `NUM_DIAS_GERAR_SLOTS = 30` em `agenda_service.py`

**Teste Manual (simular):**
1. Verificar data atual: ex: 18/12/2025
2. Calcular dia futuro: 18/12 + 30 dias = 17/01/2026
3. Verificar Google Sheets se existem slots para 17/01/2026

**Se NÃO existirem:**
4. Reiniciar o bot (isso dispara o scheduler imediatamente)
5. Verificar logs:
```
[daily_slots] Adding future slots for rolling window...
[daily_slots] Criados X novos slots para 17/01/2026
```

**Resultado Esperado:**
- Slots para 17/01/2026 foram criados
- Apenas dias úteis (seg-sex)

**Teste Automático (aguardar):**
- Aguardar até meia-noite (00:01)
- Verificar logs no dia seguinte
- Slots para o dia "hoje + 30" devem ser criados

**Critério de Sucesso:** ✅ Janela de 30 dias se mantém automaticamente

---

### **TESTE 12: Resumo Diário ao Dono**

**Objetivo:** Validar que dono recebe resumo diário às 7h.

**Configuração:**
- `OWNER_DAILY_SUMMARY_HOUR = 7` em `messages.py`

**Teste (se for após 7h):**
1. Reiniciar o bot
2. Verificar logs:
```
[daily_summary] current time past schedule hour, sending today summary now
```

3. Verificar telefone do dono

**Resultado Esperado (se houver agendamentos hoje):**
```
Agendamentos para hoje (18/12/2025):
- 14:00 Miguel Silva 5538991234567
- 15:00 João Santos 5538998765432
```

**Resultado Esperado (se NÃO houver agendamentos):**
```
Não há agendamentos para hoje (18/12/2025).
```

**Critério de Sucesso:** ✅ Resumo enviado corretamente

---

### **TESTE 13: Lembretes 24h Antes**

**Objetivo:** Validar que lembretes são enviados 24h antes do agendamento.

**Setup:**
1. Criar um agendamento para amanhã na mesma hora (ex: se agora são 14:00, agendar para amanhã 14:00)
2. Verificar aba "Lembretes" no Sheets
3. Lembrete deve ter `scheduled_iso` = hoje 14:00 (24h antes)

**Teste:**
- Aguardar até o horário do lembrete (hoje 14:00)
- Paciente deve receber no WhatsApp:

**Resultado Esperado:**
```
Olá, Miguel!
Lembrete: você tem uma consulta agendada em 19/12/2025 às 14:00.

Deseja confirmar ou cancelar?
- Confirmar
- Cancelar
```

**Passos (continuação):**
1. Clicar em "Confirmar"

**Resultado Esperado:**
```
Sua presença foi confirmada, Miguel. Obrigado!
```

**Validação:**
- Aba "Lembretes": lembrete foi removido (não marcado como enviado)

**Critério de Sucesso:** ✅ Lembrete enviado no horário correto com botões

---

## 🚨 Testes de Edge Cases

### **TESTE 14: Nenhum Dia Disponível**

**Objetivo:** Validar comportamento quando não há dias disponíveis na semana.

**Setup:**
1. Manualmente no Sheets, marcar TODOS os slots da semana atual como AGENDADO ou FOLGA

**Passos:**
2. Iniciar agendamento
3. Escolher "Esta semana"

**Resultado Esperado:**
```
Nenhum dia disponível nesta semana.
- Voltar
- Cancelar
```

**Critério de Sucesso:** ✅ Mensagem clara e botões de navegação

---

### **TESTE 15: Nenhum Horário Disponível em um Dia**

**Objetivo:** Validar comportamento quando dia não tem horários.

**Setup:**
1. Marcar todos os horários de um dia específico como AGENDADO

**Passos:**
2. Iniciar agendamento e escolher esse dia

**Resultado Esperado:**
```
Nenhum horário disponível neste dia.
- Voltar
- Cancelar
```

**Critério de Sucesso:** ✅ Mensagem clara e navegação funciona

---

### **TESTE 16: Não Há Agendamentos para Reagendar**

**Objetivo:** Validar mensagem quando não há agendamentos futuros.

**Setup:**
1. Garantir que não há agendamentos futuros no sistema

**Passos:**
2. Clicar em "Reagendar"

**Resultado Esperado:**
```
Você não possui nenhum agendamento futuro.
```

Seguido do menu principal.

**Critério de Sucesso:** ✅ Mensagem amigável

---

### **TESTE 17: Não Há Agendamentos para Cancelar**

**Objetivo:** Validar mensagem quando não há agendamentos futuros.

**Setup:**
1. Garantir que não há agendamentos futuros

**Passos:**
2. Clicar em "Cancelar Agendamento"

**Resultado Esperado:**
```
Você não possui nenhum agendamento futuro.
```

**Critério de Sucesso:** ✅ Mensagem amigável

---

### **TESTE 18: Entrada Inválida**

**Objetivo:** Validar tratamento de entradas inesperadas.

**Passos:**
1. Em qualquer lista de seleção numérica, enviar texto puro (ex: "teste")

**Resultado Esperado:**
```
Opção inválida.
```

Seguido da mensagem apropriada para escolher novamente.

**Critério de Sucesso:** ✅ Erro tratado graciosamente

---

## 📊 Checklist Final de Validação

Após executar todos os testes, verificar:

### **Funcionalidades Principais**
- [ok] Cadastro de novo usuário funciona
- [ok] Usuário existente vai direto ao menu
- [ok] Agendamento completo funciona
- [ok] Reagendamento completo funciona
- [ok] Cancelamento completo funciona
- [ok] Consulta de valores funciona

### **Notificações ao Dono**
- [ok] Notificação de novo agendamento recebida
- [ok] Notificação de cancelamento recebida
- [ok] Notificação de reagendamento (única, com dados antigos e novos) recebida
- [ok] Resumo diário recebido

### **Sistema de Slots**
- [ ] Slots criados automaticamente ao iniciar bot (30 dias)
- [ ] Scheduler diário funciona (slots adicionados à meia-noite)
- [ ] Slots com FOLGA são respeitados (não listados, não sobrescritos)

### **Google Sheets**
- [ ] Aba Agenda atualizada corretamente (AGENDADO ↔ DISPONIVEL)
- [ ] Aba Cadastros com novos usuários
- [ ] Aba Lembretes criada e gerenciada corretamente

### **Mensagens de Confirmação**
- [ ] Mensagem de agendamento exibida com emojis e formatação
- [ ] Mensagem de reagendamento específica exibida
- [ ] Mensagem de cancelamento exibida
- [ ] Menu exibido após confirmações

### **Navegação**
- [ ] Botão "Voltar" funciona em todos os níveis
- [ ] Botão "Cancelar" aborta operação e volta ao menu
- [ ] Estados são limpos corretamente após operações

### **Lembretes**
- [ ] Lembrete criado ao agendar
- [ ] Lembrete enviado 24h antes
- [ ] Lembrete com botões interativos (Confirmar/Cancelar)
- [ ] Confirmação de presença funciona
- [ ] Cancelamento via lembrete funciona

### **Edge Cases**
- [ ] Sem dias disponíveis tratado
- [ ] Sem horários disponíveis tratado
- [ ] Sem agendamentos futuros tratado
- [ ] Entradas inválidas tratadas

---

## 🐛 Registro de Bugs Encontrados

Use esta seção para anotar qualquer problema encontrado durante os testes:

| # | Teste | Problema | Gravidade | Status |
|---|-------|----------|-----------|--------|
| 1 |  |  | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |  |
| 2 |  |  | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |  |
| 3 |  |  | [ ] Crítico [ ] Alto [ ] Médio [ ] Baixo |  |

---

## ✅ Aprovação

**Testado por:** _________________
**Data:** _________________
**Resultado Geral:** [ ] ✅ Aprovado [ ] ❌ Reprovado [ok] ⚠️ Aprovado com ressalvas

**Observações:**
Coloquei uma observação para melhorar a saudação.________________
_________________________________________________________________
_________________________________________________________________

---

**Próximo passo após aprovação:** Etapa 5/6 - Refatoração de `agenda_service.py`
