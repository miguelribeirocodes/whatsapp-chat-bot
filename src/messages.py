# Arquivo de mensagens configuráveis (PT-BR)
# Modifique as constantes abaixo para personalizar textos do bot (ex.: nome da clínica)

# Identidade
CLINIC_NAME = "Clínica X"

# Mensagens gerais
# WELCOME = f"Olá! Seja bem-vindo(a) à {CLINIC_NAME}!"
WELCOME = "Olá! Seja bem-vindo(a)!"
OPERATION_CANCELLED = "Operação cancelada."
INVALID_OPTION = "Opção inválida."
WAIT_MSG = "Aguarde um momento, por favor."

# Menu principal / opções
MENU_PROMPT = f"Sou a secretária virtual da {CLINIC_NAME}."
MENU_AGENDAR = "Agendar"
MENU_REAGENDAR = "Reagendar"
MENU_CANCELAR = "Cancelar Agendamento"  # Renomeado para evitar confusão com "Cancelar operação"
MENU_SAIR = "Sair"
MENU_VALORES = "Valores e Pagamento"
MENU_LIST_TITLE = "Outras opções"

# Semanas
WEEKS_PROMPT = "Escolha a semana:"  # usado antes dos botões de semana
WEEK_THIS = "Esta semana"
WEEK_NEXT = "Próxima semana"

# Dias / listas
LIST_SECTION_TITLE = "Dias"
LIST_BUTTON_LABEL = "Ver opções"
LIST_BODY_TEXT = "Selecione uma opção"
LABEL_VOLTA = "Voltar"
LABEL_CANCEL = "Cancelar"
LABEL_CANCEL_APPOINTMENT = "Cancelar Agendamento"

# Horários
HOURS_PROMPT = "Escolha o horário:" 

# Confirmações
CONFIRM_PROMPT_TEMPLATE = "Confirma {what}?"
CONFIRM_CANCEL_APPOINTMENT_TEMPLATE = "Confirma o cancelamento do agendamento em {date} às {time}?"
CONFIRM_AGENDAMENTO_TEMPLATE = "Confirma o agendamento para {date} às {time}?"

# Rótulos de botões individuais
LABEL_CONFIRM = "Confirmar"

# Resultados - Templates de confirmação
# Template com nome do paciente: use `{name}` para inserir o primeiro nome
AGENDAMENTO_CONFIRMADO = "✅ Agendamento confirmado, {name}!"
AGENDAMENTO_CONFIRMADO_FULL = """✅ Agendamento *confirmado* com sucesso!

📅 Data: {date}
🕐 Horário: {time}

Você receberá um lembrete 24 horas antes da consulta.
Até lá!"""

REAGENDAMENTO_CONFIRMADO = """✅ Reagendamento *realizado* com sucesso!

📅 Nova data: {date}
🕐 Novo horário: {time}

O agendamento anterior foi cancelado.
Você receberá um lembrete 24 horas antes da consulta."""

CANCEL_SUCCESS_TEMPLATE = """✅ Agendamento *cancelado* com sucesso!

📅 Data: {date}
🕐 Horário: {time}

Se precisar reagendar, estou à disposição!"""

# Outros
NO_DAYS_AVAILABLE = "Nenhum dia disponível nesta semana." 
NO_HOURS_AVAILABLE = "Nenhum horário disponível neste dia." 

# Valores e formas de pagamento
PAYMENT_TITLE = "Valores e Formas de Pagamento"
PAYMENT_INFO = "Consulta: R$ 150,00. Aceitamos: Cartão, Pix e Dinheiro. O pagamento será realizado no momento da consulta." 
PAYMENT_METHODS = "Cartão, Pix, Dinheiro"

# Pedido de nome no primeiro contato
ASK_FULL_NAME = "Olá! Por favor, informe seu nome completo:" 

# Telefone do dono da clínica (string no formato internacional, ex: 551199999999)
CLINIC_OWNER_PHONE = "553899135151"

# Lembretes: número de horas antes do agendamento para envio do lembrete
# Ex.: 24 envia 24 horas antes. Pode ser ajustado conforme necessidade.
REMINDER_HOURS_BEFORE = 24

# Template de mensagem de lembrete enviada ao paciente
REMINDER_TEMPLATE = "Lembrete: você tem uma consulta agendada em {date} às {time}."

# Template de notificação enviada ao dono da clínica
OWNER_REMINDER_TEMPLATE = """📅 *NOVO AGENDAMENTO*

👤 Paciente: {patient}
📆 Data: {date}
🕐 Horário: {time}

Agendamento confirmado pelo WhatsApp."""

OWNER_REMINDER_CANCEL_TEMPLATE = """❌ *CANCELAMENTO*

👤 Paciente: {patient}
📆 Data: {date}
🕐 Horário: {time}

Agendamento cancelado pelo WhatsApp."""

OWNER_REMINDER_RESCHEDULE_TEMPLATE = """🔄 *REAGENDAMENTO*

👤 Paciente: {patient}
📆 Data anterior: {old_date}
🕐 Horário anterior: {old_time}

📆 *Nova data:* {new_date}
🕐 *Novo horário:* {new_time}

O agendamento anterior foi cancelado automaticamente."""

# Horário do resumo diário para o dono (hora local, 24h)
OWNER_DAILY_SUMMARY_HOUR = 7

# Texto curto usado no corpo do confirm de lembrete (corpo do interactive)
# Deve ser curto e não repetir a palavra 'Lembrete' para evitar duplicatas.
REMINDER_ACTION_PROMPT = "Deseja confirmar ou cancelar?"

# Mensagem enviada quando paciente confirma via botão (template com {name})
REMINDER_CONFIRMED_MSG = "Sua presença foi confirmada, {name}. Obrigado!"

# Mensagem enviada quando paciente cancela via botão
REMINDER_CANCELLED_MSG = "Seu agendamento foi cancelado. Se precisar, agende novamente. Obrigado!"
