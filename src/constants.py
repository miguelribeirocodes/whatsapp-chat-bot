"""
constants.py
Centraliza todas as constantes hardcoded do chatbot para facilitar manutenção.
"""

# ============================================================================
# BOTÕES E IDs INTERATIVOS
# ============================================================================

# IDs de Menu Principal
BUTTON_ID_AGENDAR = '1'
BUTTON_ID_REAGENDAR = '2'
BUTTON_ID_CANCELAR = '3'
BUTTON_ID_VALORES = '4'

# IDs de Navegação Universal
BUTTON_ID_VOLTAR = '0'
BUTTON_ID_CANCELAR_OPERACAO = '9'

# IDs de Confirmação
BUTTON_ID_CONFIRMAR = '1'

# IDs de Seleção de Semana
BUTTON_ID_ESTA_SEMANA = '1'
BUTTON_ID_PROXIMA_SEMANA = '2'

# ============================================================================
# CHAVES DE SESSÃO (Session Keys)
# ============================================================================

class SessionKeys:
    """Centraliza todas as chaves usadas no dicionário de sessões."""

    # Estado atual do usuário
    STATE = ''  # sessoes[usuario_id]

    # Dados do usuário
    FIRST_NAME = '_first_name'  # sessoes[usuario_id + '_first_name']

    # Dados do fluxo de agendamento
    SEMANA_OFFSET = '_semana_offset'  # 0 ou 1
    DIA_ESCOLHIDO = '_dia_escolhido'  # date object
    HORARIO_ESCOLHIDO = '_horario_escolhido'  # datetime object

    # Dados de reagendamento
    REAGENDAR_ANTIGO = '_reagendar_antigo'  # datetime do agendamento antigo

    # Dados de cancelamento
    CANCEL_TARGET = '_cancel_target'  # datetime do agendamento a cancelar
    PREV_STATE = '_prev_state'  # estado anterior (para voltar)

    # Listas compartilhadas (⚠️ usar com cuidado - não são por usuário)
    LISTA_AGENDAMENTOS = '_lista_agendamentos'
    LISTA_AGENDAMENTOS_CANCELAR = '_lista_agendamentos_cancelar'

    @staticmethod
    def get_user_key(usuario_id: str, key_suffix: str) -> str:
        """Helper para gerar chave de sessão do usuário."""
        if key_suffix == '':
            return usuario_id
        return f"{usuario_id}{key_suffix}"


# ============================================================================
# ESTADOS DA MÁQUINA DE ESTADOS
# ============================================================================

class States:
    """Define todos os estados possíveis do chatbot."""
    MENU_PRINCIPAL = 'menu_principal'
    AGENDAR = 'agendar'
    REAGENDAR = 'reagendar'
    CANCELAR = 'cancelar'
    ESCOLHER_SEMANA = 'escolher_semana'
    ESCOLHER_DIA = 'escolher_dia'
    ESCOLHER_HORARIO = 'escolher_horario'
    CONFIRMAR = 'confirmar'
    CONFIRM_CANCEL = 'confirm_cancel'
    CONFIRM_CANCEL_APPOINTMENT = 'confirm_cancel_appointment'
    ESPERAR_NOME = 'esperar_nome'  # Novo estado para primeiro contato


# ============================================================================
# TRANSIÇÕES VÁLIDAS (State Machine Validation)
# ============================================================================

VALID_TRANSITIONS = {
    States.MENU_PRINCIPAL: [
        States.AGENDAR,
        States.REAGENDAR,
        States.CANCELAR,
        States.MENU_PRINCIPAL,  # Permite ficar no mesmo estado
    ],
    States.AGENDAR: [
        States.ESCOLHER_DIA,
        States.MENU_PRINCIPAL,
    ],
    States.ESCOLHER_DIA: [
        States.ESCOLHER_HORARIO,
        States.AGENDAR,  # Voltar para escolher semana
        States.MENU_PRINCIPAL,  # Cancelar operação
    ],
    States.ESCOLHER_HORARIO: [
        States.CONFIRMAR,
        States.ESCOLHER_DIA,  # Voltar para escolher dia
        States.MENU_PRINCIPAL,  # Cancelar operação
    ],
    States.CONFIRMAR: [
        States.MENU_PRINCIPAL,  # Após confirmar ou cancelar
        States.ESCOLHER_HORARIO,  # Voltar para escolher horário
    ],
    States.REAGENDAR: [
        States.AGENDAR,  # Após escolher qual agendamento reagendar
        States.MENU_PRINCIPAL,  # Voltar ou cancelar
    ],
    States.CANCELAR: [
        States.CONFIRM_CANCEL_APPOINTMENT,
        States.MENU_PRINCIPAL,
    ],
    States.CONFIRM_CANCEL_APPOINTMENT: [
        States.MENU_PRINCIPAL,
        States.CANCELAR,  # Voltar para lista
    ],
}


# ============================================================================
# AÇÕES UNIVERSAIS (Reconhecidas em qualquer estado)
# ============================================================================

class UniversalActions:
    """Define ações que funcionam em qualquer estado."""

    # Palavras-chave para voltar
    BACK_KEYWORDS = {'0', 'voltar', '⬅️'}

    # Palavras-chave para cancelar operação
    CANCEL_KEYWORDS = {'9', 'cancelar', 'cancel'}

    @staticmethod
    def is_back_action(mensagem: str) -> bool:
        """Verifica se a mensagem é uma ação de voltar."""
        if not mensagem:
            return False
        return str(mensagem).strip().lower() in UniversalActions.BACK_KEYWORDS

    @staticmethod
    def is_cancel_action(mensagem: str) -> bool:
        """Verifica se a mensagem é uma ação de cancelar."""
        if not mensagem:
            return False
        return str(mensagem).strip().lower() in UniversalActions.CANCEL_KEYWORDS


# ============================================================================
# CONFIGURAÇÕES DE HORÁRIOS (De agenda_service.py)
# ============================================================================

class ScheduleConfig:
    """Configurações de horários de atendimento."""

    # Horários de funcionamento
    HORA_INICIO_MANHA = (8, 0)  # 08:00
    HORA_FIM_MANHA = (12, 0)    # 12:00
    HORA_INICIO_TARDE = (14, 0)  # 14:00
    HORA_FIM_TARDE = (17, 0)     # 17:00

    # Duração e intervalos
    DURACAO_CONSULTA_MIN = 50
    INTERVALO_DESCANSO_MIN = 10

    # Dias de trabalho (0=segunda, 4=sexta)
    DIAS_UTEIS = {0, 1, 2, 3, 4}

    # Quantos dias no futuro gerar slots
    NUM_DIAS_GERAR_SLOTS = 30


# ============================================================================
# CONFIGURAÇÕES DE LEMBRETES
# ============================================================================

class ReminderConfig:
    """Configurações de lembretes."""

    # Horas antes do agendamento para enviar lembrete
    HOURS_BEFORE = 24

    # Hora do dia para enviar resumo diário ao dono
    DAILY_SUMMARY_HOUR = 7


# ============================================================================
# LIMITES DA API DO WHATSAPP
# ============================================================================

class WhatsAppLimits:
    """Limites impostos pela API do WhatsApp."""

    # Limite de caracteres para header de lista
    LIST_HEADER_MAX_CHARS = 60

    # Limite de caracteres para título de item de lista
    LIST_ROW_TITLE_MAX_CHARS = 24

    # Número máximo de botões de resposta rápida
    MAX_REPLY_BUTTONS = 3


# ============================================================================
# ESTRUTURA DO GOOGLE SHEETS
# ============================================================================

class SheetColumns:
    """Índices das colunas nas planilhas do Google Sheets."""

    # Aba "Agenda"
    AGENDA_DIA_SEMANA = 0  # A - Nome do dia da semana
    AGENDA_DATA = 1        # B - Data (DD/MM/YYYY)
    AGENDA_HORA = 2        # C - Hora (HH:MM)
    AGENDA_NOME = 3        # D - Nome do paciente
    AGENDA_TELEFONE = 4    # E - Telefone
    AGENDA_STATUS = 5      # F - Status (LIVRE, AGENDADO, CANCELADO, FOLGA)
    AGENDA_ORIGEM = 6      # G - Origem (web, whatsapp, etc.)
    AGENDA_OBSERVACOES = 7 # H - Observações

    # Status possíveis
    STATUS_LIVRE = 'LIVRE'
    STATUS_AGENDADO = 'AGENDADO'
    STATUS_CANCELADO = 'CANCELADO'
    STATUS_FOLGA = 'FOLGA'

    # Aba "Cadastros"
    CADASTRO_TELEFONE = 0  # A - Telefone
    CADASTRO_NOME = 1      # B - Nome completo
    CADASTRO_ORIGEM = 2    # C - Origem
    CADASTRO_DATA_CADASTRO = 3  # D - Data de cadastro

    # Aba "Lembretes"
    LEMBRETE_SCHEDULED_DT = 0     # A - Quando enviar
    LEMBRETE_APPOINTMENT_ISO = 1  # B - ISO datetime do agendamento
    LEMBRETE_TELEFONE = 2         # C - Telefone do paciente
    LEMBRETE_PACIENTE = 3         # D - Nome do paciente
    LEMBRETE_TIPO = 4             # E - Tipo de lembrete
    LEMBRETE_ENVIADO = 5          # F - Status (PENDENTE/ENVIADO)
    LEMBRETE_OBSERVACOES = 6      # G - Observações


# ============================================================================
# NOMES DOS DIAS DA SEMANA
# ============================================================================

NOMES_DIAS_PT = [
    'Segunda',
    'Terça',
    'Quarta',
    'Quinta',
    'Sexta',
    'Sábado',
    'Domingo'
]

NOMES_DIAS_ABREV_PT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
