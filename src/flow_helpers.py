"""
flow_helpers.py
Funções auxiliares para o fluxo do chatbot - elimina código duplicado.
"""

from datetime import datetime, date
from typing import List, Tuple, Optional
from src.constants import NOMES_DIAS_PT


# ============================================================================
# FORMATAÇÃO DE DATAS
# ============================================================================

def format_data_pt(dt: Optional[date]) -> str:
    """
    Formata uma data em português.
    Exemplo: "Segunda-feira, 23/12/2025"
    """
    if dt is None:
        return ''
    weekday_name = NOMES_DIAS_PT[dt.weekday()]
    return f"{weekday_name}, {dt.day:02d}/{dt.month:02d}/{dt.year}"


def format_hora(dt: datetime) -> str:
    """
    Formata apenas a hora de um datetime.
    Exemplo: "14:30"
    """
    return dt.strftime('%H:%M')


def format_data_hora_completa(dt: datetime) -> str:
    """
    Formata data e hora completa.
    Exemplo: "Segunda-feira, 23/12/2025 às 14:30"
    """
    return f"{format_data_pt(dt.date())} às {format_hora(dt)}"


# ============================================================================
# EXTRAÇÃO DE ÍNDICE DE MENSAGEM
# ============================================================================

def parse_index_from_message(mensagem: str) -> int:
    """
    Tenta extrair um número de uma mensagem como '1', 'd1', 't2' etc.
    Retorna o número inteiro encontrado, ou lança ValueError se não achar.
    """
    import re
    if mensagem is None:
        raise ValueError("mensagem vazia")
    m = re.search(r"(\d+)", str(mensagem))
    if not m:
        raise ValueError("nenhum dígito encontrado")
    return int(m.group(1))


# ============================================================================
# FORMATAÇÃO DE LISTAS DE AGENDAMENTOS (Elimina duplicação!)
# ============================================================================

def format_appointment_list(
    agendamentos: List[Tuple[datetime, List]],
    action_verb: str = 'reagendar'
) -> str:
    """
    Formata uma lista de agendamentos para exibição ao usuário.

    Args:
        agendamentos: Lista de tuplas (datetime, linha_sheet)
        action_verb: 'reagendar' ou 'cancelar'

    Returns:
        Texto formatado para envio ao usuário

    Exemplo de uso:
        texto = format_appointment_list(agendamentos, 'reagendar')
        # Resultado:
        # "Escolha o agendamento para reagendar:
        #  1️⃣ Segunda, 23/12/2025 10:00 - Miguel
        #  2️⃣ Terça, 24/12/2025 14:00 - João
        #  ⬅️ Voltar"
    """
    import messages as MSG

    texto = f"Escolha o agendamento para {action_verb}:\n"

    for idx, (dt, linha) in enumerate(agendamentos):
        # Nome do paciente (coluna 3 do sheet)
        nome = linha[3] if len(linha) > 3 else "Paciente"
        nome = nome or "Paciente"

        # Formato: "1️⃣ Segunda, 23/12 10:00 - Miguel"
        texto += f"{idx+1}️⃣ {format_data_pt(dt)} {format_hora(dt)} - {nome}\n"

    texto += f"⬅️ {MSG.LABEL_VOLTA}"
    return texto


# ============================================================================
# FORMATAÇÃO DE LISTA DE DIAS
# ============================================================================

def format_days_list(dias: List[date]) -> str:
    """
    Formata uma lista de datas (dias) para exibição.

    Returns:
        Texto formatado para envio ao usuário
    """
    import messages as MSG

    if not dias:
        return f"{MSG.NO_DAYS_AVAILABLE}\n⬅️ {MSG.LABEL_VOLTA}"

    texto = "Escolha o dia:\n"
    for idx, dia in enumerate(dias):
        texto += f"{idx+1}️⃣ {format_data_pt(dia)}\n"
    texto += f"⬅️ {MSG.LABEL_VOLTA}"
    return texto


# ============================================================================
# FORMATAÇÃO DE LISTA DE HORÁRIOS
# ============================================================================

def format_hours_list(horarios: List[datetime]) -> str:
    """
    Formata uma lista de horários para exibição.

    Returns:
        Texto formatado para envio ao usuário
    """
    import messages as MSG

    if not horarios:
        return f"{MSG.NO_HOURS_AVAILABLE}\n⬅️ {MSG.LABEL_VOLTA}"

    texto = "Escolha o horário:\n"
    for idx, h in enumerate(horarios):
        texto += f"{idx+1}️⃣ {format_hora(h)}\n"
    texto += f"⬅️ {MSG.LABEL_VOLTA}"
    return texto


# ============================================================================
# VALIDAÇÃO DE SELEÇÃO
# ============================================================================

def is_valid_selection(index: int, items_list: List) -> bool:
    """
    Verifica se um índice é válido para uma lista.

    Args:
        index: Índice selecionado (0-based)
        items_list: Lista de itens

    Returns:
        True se o índice é válido, False caso contrário
    """
    return 0 <= index < len(items_list)


# ============================================================================
# LIMPEZA DE SESSÃO
# ============================================================================

def cleanup_session_keys(sessoes: dict, usuario_id: str, keys_to_clean: List[str]):
    """
    Remove múltiplas chaves de sessão de uma vez.

    Args:
        sessoes: Dicionário de sessões
        usuario_id: ID do usuário
        keys_to_clean: Lista de sufixos de chaves para limpar

    Exemplo:
        cleanup_session_keys(sessoes, 'user123', [
            '_semana_offset',
            '_dia_escolhido',
            '_horario_escolhido'
        ])
    """
    from constants import SessionKeys

    for key_suffix in keys_to_clean:
        full_key = SessionKeys.get_user_key(usuario_id, key_suffix)
        sessoes.pop(full_key, None)


def cleanup_agendamento_session(sessoes: dict, usuario_id: str):
    """
    Limpa todas as chaves de sessão relacionadas ao agendamento.
    """
    cleanup_session_keys(sessoes, usuario_id, [
        '_semana_offset',
        '_dia_escolhido',
        '_horario_escolhido',
        '_reagendar_antigo'
    ])


def cleanup_cancelamento_session(sessoes: dict, usuario_id: str):
    """
    Limpa todas as chaves de sessão relacionadas ao cancelamento.
    """
    cleanup_session_keys(sessoes, usuario_id, [
        '_cancel_target',
        '_prev_state'
    ])
    # Limpar lista compartilhada
    sessoes.pop('_lista_agendamentos_cancelar', None)


# ============================================================================
# OBTENÇÃO DE AGENDAMENTOS FUTUROS (Elimina duplicação!)
# ============================================================================

def get_future_appointments(usuario_id: str = None) -> List[Tuple[datetime, List]]:
    """
    Obtém todos os agendamentos futuros, opcionalmente filtrados por usuário.

    Args:
        usuario_id: Telefone do usuário (opcional, se None retorna todos)

    Returns:
        Lista ordenada de tuplas (datetime, linha_sheet)
    """
    from agenda_service import obter_todos_agenda_cached
    from constants import SheetColumns

    todos = obter_todos_agenda_cached()[1:]  # Ignora cabeçalho
    agora = datetime.now()
    agendamentos = []

    for linha in todos:
        # Validação básica
        if len(linha) < 6:
            continue

        # Apenas agendamentos confirmados
        status = linha[SheetColumns.AGENDA_STATUS].strip().upper()
        if status != SheetColumns.STATUS_AGENDADO:
            continue

        # Parse data e hora
        data_str = linha[SheetColumns.AGENDA_DATA].strip()
        hora_str = linha[SheetColumns.AGENDA_HORA].strip()
        try:
            dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
        except Exception:
            continue

        # Apenas futuros
        if dt < agora:
            continue

        # Filtro opcional por usuário
        if usuario_id:
            telefone = linha[SheetColumns.AGENDA_TELEFONE].strip()
            if telefone != usuario_id:
                continue

        agendamentos.append((dt, linha))

    # Ordenar por data/hora
    agendamentos.sort()
    return agendamentos


# ============================================================================
# GERADORES DE MENSAGENS DE CONFIRMAÇÃO
# ============================================================================

def create_confirmation_message(dt: datetime, action: str = 'agendamento') -> str:
    """
    Cria mensagem de confirmação formatada.

    Args:
        dt: Data/hora do agendamento
        action: 'agendamento' ou 'cancelamento'

    Returns:
        Mensagem formatada
    """
    import messages as MSG

    if action == 'agendamento':
        return MSG.CONFIRM_AGENDAMENTO_TEMPLATE.format(
            date=format_data_pt(dt),
            time=format_hora(dt)
        )
    elif action == 'cancelamento':
        return MSG.CONFIRM_CANCEL_APPOINTMENT_TEMPLATE.format(
            date=format_data_pt(dt),
            time=format_hora(dt)
        )
    else:
        raise ValueError(f"Ação desconhecida: {action}")


# ============================================================================
# CONSTRUTOR DE MENU PRINCIPAL
# ============================================================================

def build_main_menu() -> Tuple[str, List[Tuple[str, str, str]]]:
    """
    Constrói o menu principal com texto e items.

    Returns:
        Tupla (texto, items) onde items = [(id, title, description), ...]
    """
    import messages as MSG
    from constants import BUTTON_ID_AGENDAR, BUTTON_ID_REAGENDAR, BUTTON_ID_CANCELAR, BUTTON_ID_VALORES

    texto = f"{MSG.MENU_PROMPT}\n{MSG.LIST_BODY_TEXT}"
    items = [
        (BUTTON_ID_AGENDAR, MSG.MENU_AGENDAR, ""),
        (BUTTON_ID_REAGENDAR, MSG.MENU_REAGENDAR, ""),
        (BUTTON_ID_CANCELAR, MSG.MENU_CANCELAR, ""),
        (BUTTON_ID_VALORES, MSG.MENU_VALORES, ""),
    ]
    return texto, items


# ============================================================================
# BUILDER DE MENSAGEM DE RETORNO AO MENU
# ============================================================================

def build_return_to_menu_message(prefix_message: str = "") -> str:
    """
    Constrói mensagem de retorno ao menu principal.

    Args:
        prefix_message: Mensagem adicional antes do menu (ex: "Operação cancelada.")

    Returns:
        Mensagem completa formatada
    """
    menu_text, _ = build_main_menu()
    if prefix_message:
        return f"{prefix_message}\n{menu_text}"
    return menu_text
