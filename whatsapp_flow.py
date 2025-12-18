"""
whatsapp_flow.py
Fluxo principal do chatbot de agendamento via WhatsApp (sem IA).
Menu guiado com opções: Agendar, Reagendar, Cancelar, Sair.
Navegação por datas, horários e confirmação, mantendo integração com agenda_service.py.
"""

from agenda_service import *
import re
import messages as MSG
import logging

logger = logging.getLogger(__name__)

# Helper: weekday names in Portuguese
_WEEKDAY_PT = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
]

def _format_data_pt(dt):
    if dt is None:
        return ''
    return f"{_WEEKDAY_PT[dt.weekday()]}, {dt.day:02d}/{dt.month:02d}/{dt.year}"



def _parse_index_from_message(mensagem: str) -> int:
    """Tenta extrair um número de uma mensagem como '1', 'd1', 't2' etc.
    Retorna o número inteiro encontrado, ou lança ValueError se não achar.
    """
    if mensagem is None:
        raise ValueError("mensagem vazia")
    m = re.search(r"(\d+)", str(mensagem))
    if not m:
        raise ValueError("nenhum dígito encontrado")
    return int(m.group(1))

# Estados possíveis do usuário
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
SAIR = 'sair'

# Simulação de sessão do usuário (em produção, usar banco ou cache)
sessoes = {}

def exibir_menu_principal():
    return (
        f"{MSG.MENU_PROMPT}\n"
        f"1️⃣ {MSG.MENU_AGENDAR}\n"
        f"2️⃣ {MSG.MENU_REAGENDAR}\n"
        f"3️⃣ {MSG.MENU_CANCELAR}\n"
        f"4️⃣ {MSG.MENU_SAIR}\n"
    )

def processar_mensagem(usuario_id, mensagem):
    # Obter estado atual do usuário
    estado = sessoes.get(usuario_id, MENU_PRINCIPAL)

    # Normalizar mensagem para decisões simples
    texto_normalizado = (mensagem or "").strip().lower()
    is_back = (texto_normalizado in ('0', 'voltar')) or (mensagem == '⬅️')
    is_cancel = (texto_normalizado in ('9', 'cancelar', 'cancel'))
    # Helper to restore previous state when user backs out from a confirm dialog
    def _restore_prev_state():
        prev = sessoes.pop(usuario_id + '_prev_state', None)
        if prev:
            sessoes[usuario_id] = prev
            return prev
        sessoes[usuario_id] = MENU_PRINCIPAL
        return MENU_PRINCIPAL
    # Responder a saudações com o menu principal (inclui cumprimento)
    if estado == MENU_PRINCIPAL and texto_normalizado in ("oi", "olá", "ola", "boa tarde", "bom dia", "boa noite"):
        return MSG.WELCOME + "\n" + exibir_menu_principal()

    if estado == MENU_PRINCIPAL:
        if mensagem == '1':
            sessoes[usuario_id] = AGENDAR
            sessoes[usuario_id + '_semana_offset'] = 0
            return exibir_semanas_disponiveis(usuario_id)
        elif mensagem == '2':
            sessoes[usuario_id] = REAGENDAR
            return processar_mensagem(usuario_id, '')
        elif mensagem == '3':
            sessoes[usuario_id] = CANCELAR
            # trigger cancel flow initial listing
            return processar_mensagem(usuario_id, '')
        elif mensagem == '4':
            sessoes[usuario_id] = SAIR
            return "Até logo!"
        else:
            return MSG.INVALID_OPTION + " Escolha uma das opções abaixo:\n" + exibir_menu_principal()

    if estado == AGENDAR:
        # Navegação entre semanas
        if is_cancel:
            # abort and return to main menu
            sessoes[usuario_id] = MENU_PRINCIPAL
            # clear interim keys
            sessoes.pop(usuario_id + '_semana_offset', None)
            sessoes.pop(usuario_id + '_dia_escolhido', None)
            sessoes.pop(usuario_id + '_horario_escolhido', None)
            return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
        if mensagem == '1':  # Esta semana
            sessoes[usuario_id + '_semana_offset'] = 0
            sessoes[usuario_id] = ESCOLHER_DIA
            return exibir_dias_disponiveis(usuario_id, 0)
        elif mensagem == '2':  # Próxima semana
            sessoes[usuario_id + '_semana_offset'] = 1
            sessoes[usuario_id] = ESCOLHER_DIA
            return exibir_dias_disponiveis(usuario_id, 1)
        elif is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            return exibir_menu_principal()
        else:
            return MSG.INVALID_OPTION + ". Escolha uma semana:\n" + exibir_semanas_disponiveis(usuario_id)

    if estado == REAGENDAR:
        # Listar todos os agendamentos futuros e permitir escolha
        if '_lista_agendamentos' not in sessoes:
            from agenda_service import obter_todos_agenda_cached
            from datetime import datetime
            todos = obter_todos_agenda_cached()[1:]  # ignora cabeçalho (cached)
            agora = datetime.now()
            agendamentos = []
            for linha in todos:
                if len(linha) < 6:
                    continue
                status = linha[5].strip().upper()
                if status != 'AGENDADO':
                    continue
                data_str = linha[1].strip()
                hora_str = linha[2].strip()
                try:
                    dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
                except Exception:
                    continue
                if dt < agora:
                    continue
                agendamentos.append((dt, linha))
            agendamentos.sort()
            sessoes['_lista_agendamentos'] = agendamentos
            if not agendamentos:
                sessoes[usuario_id] = MENU_PRINCIPAL
                return "Nenhum agendamento futuro encontrado.\n" + exibir_menu_principal()
            texto = "Escolha o agendamento para reagendar:\n"
            for idx, (dt, linha) in enumerate(agendamentos):
                nome = linha[3] or "Paciente"
                texto += f"{idx+1}️⃣ {_format_data_pt(dt)} {dt.strftime('%H:%M')} - {nome}\n"
            texto += f"⬅️ {MSG.LABEL_VOLTA}"
            return texto
        if is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop('_lista_agendamentos', None)
            return exibir_menu_principal()
        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop('_lista_agendamentos', None)
            return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
        try:
            idx = int(mensagem) - 1
            agendamentos = sessoes['_lista_agendamentos']
            if 0 <= idx < len(agendamentos):
                dt, linha = agendamentos[idx]
                sessoes[usuario_id + '_reagendar_antigo'] = dt
                sessoes[usuario_id] = AGENDAR
                sessoes.pop('_lista_agendamentos', None)
                return "Escolha a nova data e horário:\n" + exibir_semanas_disponiveis(usuario_id)
            else:
                # rebuild the list from the session and return without recursing
                agendamentos = sessoes.get('_lista_agendamentos', [])
                texto = "Escolha o agendamento para reagendar:\n"
                for idx2, (dt2, linha2) in enumerate(agendamentos):
                    nome2 = linha2[3] or "Paciente"
                    texto += f"{idx2+1}️⃣ {_format_data_pt(dt2)} {dt2.strftime('%H:%M')} - {nome2}\n"
                texto += f"⬅️ {MSG.LABEL_VOLTA}"
                return MSG.INVALID_OPTION + " Escolha um agendamento:\n" + texto
        except Exception:
            agendamentos = sessoes.get('_lista_agendamentos', [])
            texto = "Escolha o agendamento para reagendar:\n"
            for idx2, (dt2, linha2) in enumerate(agendamentos):
                nome2 = linha2[3] or "Paciente"
                texto += f"{idx2+1}️⃣ {_format_data_pt(dt2)} {dt2.strftime('%H:%M')} - {nome2}\n"
            texto += f"⬅️ {MSG.LABEL_VOLTA}"
            return MSG.INVALID_OPTION + " Escolha um agendamento:\n" + texto

    if estado == CANCELAR:
        # Listar todos os agendamentos futuros e permitir escolha
        if '_lista_agendamentos_cancelar' not in sessoes:
            from agenda_service import obter_todos_agenda_cached, cancelar_agendamento_por_data_hora
            from datetime import datetime
            todos = obter_todos_agenda_cached()[1:]  # ignora cabeçalho (cached)
            agora = datetime.now()
            agendamentos = []
            for linha in todos:
                if len(linha) < 6:
                    continue
                status = linha[5].strip().upper()
                if status != 'AGENDADO':
                    continue
                data_str = linha[1].strip()
                hora_str = linha[2].strip()
                try:
                    dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
                except Exception:
                    continue
                if dt < agora:
                    continue
                agendamentos.append((dt, linha))
            agendamentos.sort()
            sessoes['_lista_agendamentos_cancelar'] = agendamentos
            if not agendamentos:
                sessoes[usuario_id] = MENU_PRINCIPAL
                return "Nenhum agendamento futuro encontrado.\n" + exibir_menu_principal()
            texto = "Escolha o agendamento para cancelar:\n"
            for idx, (dt, linha) in enumerate(agendamentos):
                nome = linha[3] or "Paciente"
                texto += f"{idx+1}️⃣ {_format_data_pt(dt)} {dt.strftime('%H:%M')} - {nome}\n"
            texto += f"⬅️ {MSG.LABEL_VOLTA}"
            return texto
        if is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop('_lista_agendamentos_cancelar', None)
            return exibir_menu_principal()
        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop('_lista_agendamentos_cancelar', None)
            return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
        try:
            idx = int(mensagem) - 1
            agendamentos = sessoes['_lista_agendamentos_cancelar']
            if 0 <= idx < len(agendamentos):
                dt, linha = agendamentos[idx]
                # ask for confirmation before cancelling the selected appointment
                sessoes[usuario_id + '_cancel_target'] = dt
                sessoes[usuario_id + '_prev_state'] = CANCELAR
                sessoes[usuario_id] = CONFIRM_CANCEL_APPOINTMENT
                return MSG.CONFIRM_CANCEL_APPOINTMENT_TEMPLATE.format(date=_format_data_pt(dt), time=dt.strftime('%H:%M'))
            else:
                agendamentos = sessoes.get('_lista_agendamentos_cancelar', [])
                texto = "Escolha o agendamento para cancelar:\n"
                for idx2, (dt2, linha2) in enumerate(agendamentos):
                    nome2 = linha2[3] or "Paciente"
                    texto += f"{idx2+1}️⃣ {_format_data_pt(dt2)} {dt2.strftime('%H:%M')} - {nome2}\n"
                texto += f"⬅️ {MSG.LABEL_VOLTA}"
                return MSG.INVALID_OPTION + " Escolha um agendamento:\n" + texto
        except Exception:
            agendamentos = sessoes.get('_lista_agendamentos_cancelar', [])
            texto = "Escolha o agendamento para cancelar:\n"
            for idx2, (dt2, linha2) in enumerate(agendamentos):
                nome2 = linha2[3] or "Paciente"
                texto += f"{idx2+1}️⃣ {_format_data_pt(dt2)} {dt2.strftime('%H:%M')} - {nome2}\n"
            texto += f"⬅️ {MSG.LABEL_VOLTA}"
            return MSG.INVALID_OPTION + " Escolha um agendamento:\n" + texto

    if estado == ESCOLHER_DIA:
        try:
            if is_cancel:
                # cancelar imediatamente a operação atual e voltar ao menu principal
                sessoes[usuario_id] = MENU_PRINCIPAL
                # limpar chaves intermédias
                sessoes.pop(usuario_id + '_semana_offset', None)
                sessoes.pop(usuario_id + '_dia_escolhido', None)
                sessoes.pop(usuario_id + '_horario_escolhido', None)
                return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
            if is_back:
                # voltar para seleção de semana (onde o usuário escolhe 'Esta semana'/'Próxima semana')
                sessoes[usuario_id] = AGENDAR
                return exibir_semanas_disponiveis(usuario_id)
            dia_idx = int(mensagem) - 1
            semana_offset = sessoes.get(usuario_id + '_semana_offset', 0)
            dias = obter_dias_disponiveis_semana(semana_offset)
            if 0 <= dia_idx < len(dias):
                sessoes[usuario_id + '_dia_escolhido'] = dias[dia_idx]
                sessoes[usuario_id] = ESCOLHER_HORARIO
                return exibir_horarios_disponiveis(usuario_id, dias[dia_idx])
            else:
                return MSG.INVALID_OPTION + ". Escolha um dia:\n" + exibir_dias_disponiveis(usuario_id, semana_offset)
        except Exception:
            return MSG.INVALID_OPTION + ". Escolha um dia:\n" + exibir_dias_disponiveis(usuario_id, sessoes.get(usuario_id + '_semana_offset', 0))

    if estado == ESCOLHER_HORARIO:
        try:
            if is_cancel:
                # cancelar imediatamente a operação atual e voltar ao menu principal
                sessoes[usuario_id] = MENU_PRINCIPAL
                # limpar escolhas intermédias
                sessoes.pop(usuario_id + '_horario_escolhido', None)
                sessoes.pop(usuario_id + '_dia_escolhido', None)
                return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
            if is_back:
                # voltar para seleção de dia (permitir escolher outro dia da mesma semana)
                sessoes[usuario_id] = ESCOLHER_DIA
                semana_offset = sessoes.get(usuario_id + '_semana_offset', 0)
                return exibir_dias_disponiveis(usuario_id, semana_offset)
            horario_idx = int(mensagem) - 1
            dia_escolhido = sessoes.get(usuario_id + '_dia_escolhido')
            horarios = obter_horarios_disponiveis_para_dia(dia_escolhido)
            if 0 <= horario_idx < len(horarios):
                sessoes[usuario_id + '_horario_escolhido'] = horarios[horario_idx]
                sessoes[usuario_id] = CONFIRMAR
                return MSG.CONFIRM_AGENDAMENTO_TEMPLATE.format(date=_format_data_pt(horarios[horario_idx]), time=horarios[horario_idx].strftime('%H:%M'))
            else:
                return MSG.INVALID_OPTION + ". Escolha um horário:\n" + exibir_horarios_disponiveis(usuario_id, dia_escolhido)
        except Exception:
            return MSG.INVALID_OPTION + ". Escolha um horário:\n" + exibir_horarios_disponiveis(usuario_id, sessoes.get(usuario_id + '_dia_escolhido'))

    if estado == CONFIRMAR:
        logger.debug('[flow] CONFIRMAR state received mensagem=%s is_cancel=%s', mensagem, is_cancel)
        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            # clear interim choices
            sessoes.pop(usuario_id + '_horario_escolhido', None)
            sessoes.pop(usuario_id + '_dia_escolhido', None)
            return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()
        if mensagem == '1':
            horario = sessoes.get(usuario_id + '_horario_escolhido')
            # Se for reagendamento, cancelar o antigo
            if sessoes.get(usuario_id + '_reagendar_antigo'):
                from agenda_service import cancelar_agendamento_por_data_hora
                cancelar_agendamento_por_data_hora(sessoes[usuario_id + '_reagendar_antigo'])
                sessoes.pop(usuario_id + '_reagendar_antigo', None)
            # Use the real phone number (usuario_id) and patient name if available
            nome_paciente = sessoes.get(usuario_id + '_first_name') or "Paciente WhatsApp"
            registrar_agendamento_google_sheets(
                nome_paciente=nome_paciente,
                data_hora_consulta=horario,
                origem="whatsapp_simulado",
                telefone=usuario_id,
                observacoes="Agendado via menu bot"
            )
            # Persist and schedule reminders: patient reminder and notify owner immediately
            try:
                from agenda_service import registrar_lembrete_agendamento, marcar_lembrete_como_enviado
                from scheduler import schedule_at
                from datetime import timedelta, datetime
                reminder_dt = horario - timedelta(hours=MSG.REMINDER_HOURS_BEFORE)
                # register reminder in sheet (returns row index)
                try:
                    row_idx = registrar_lembrete_agendamento(horario, reminder_dt, usuario_id, nome_paciente, tipo="patient_reminder", observacoes="Agendado via bot")
                except Exception:
                    row_idx = None
                # schedule in-memory job
                def _send_and_mark(row=row_idx, phone=usuario_id, dt=horario, patient=nome_paciente):
                    try:
                        # personalize with first name when available
                        primeiro = (patient or '').split()[0] if patient else ''
                        greeting = f"Olá, {primeiro}!\n" if primeiro else ''
                        appt_text = MSG.REMINDER_TEMPLATE.format(date=dt.strftime('%d/%m/%Y'), time=dt.strftime('%H:%M'))
                        action = MSG.REMINDER_ACTION_PROMPT if hasattr(MSG, 'REMINDER_ACTION_PROMPT') else ''
                        text = greeting + appt_text + ("\n" + action if action else "")
                        __import__('whatsapp_webhook').send_reminder_confirm_buttons(phone, text, dt.isoformat())
                    except Exception:
                        __import__('logging').getLogger('whatsapp_flow').exception('failed sending reminder')
                    try:
                        if row:
                            __import__('agenda_service').marcar_lembrete_como_enviado(row)
                    except Exception:
                        pass

                if reminder_dt > datetime.now():
                    schedule_at(reminder_dt, _send_and_mark)
                else:
                    # scheduled time already passed -> send immediately and mark
                    _send_and_mark()

                # notify owner immediately (if configured)
                try:
                    __import__('whatsapp_webhook').send_reminder_to_owner(nome_paciente, horario.strftime('%d/%m/%Y'), horario.strftime('%H:%M'))
                except Exception:
                    pass
            except Exception:
                pass
            sessoes[usuario_id] = MENU_PRINCIPAL
            nome_para_msg = nome_paciente.split()[0] if nome_paciente else ''
            return MSG.AGENDAMENTO_CONFIRMADO.format(name=nome_para_msg) + "\n" + exibir_menu_principal()
        elif is_back:
            sessoes[usuario_id] = ESCOLHER_HORARIO
            return exibir_horarios_disponiveis(usuario_id, sessoes.get(usuario_id + '_dia_escolhido'))
        else:
            return MSG.INVALID_OPTION + " Confirme ou volte:\n1️⃣ Confirmar\n⬅️ " + MSG.LABEL_VOLTA

    # Nota: confirmação genérica de cancelar removida; cancelamentos de operação agora abortam imediatamente

    if estado == CONFIRM_CANCEL_APPOINTMENT:
        logger.debug('[flow] CONFIRM_CANCEL_APPOINTMENT state received mensagem=%s is_cancel=%s', mensagem, is_cancel)
        if mensagem == '1':
            dt = sessoes.pop(usuario_id + '_cancel_target', None)
            from agenda_service import cancelar_agendamento_por_data_hora
            sucesso = False
            if dt:
                sucesso = cancelar_agendamento_por_data_hora(dt)
            sessoes.pop(usuario_id + '_prev_state', None)
            sessoes.pop('_lista_agendamentos_cancelar', None)
            sessoes[usuario_id] = MENU_PRINCIPAL
            if sucesso:
                return MSG.CANCEL_SUCCESS_TEMPLATE.format(date=_format_data_pt(dt), time=dt.strftime('%H:%M')) + "\n" + exibir_menu_principal()
            else:
                return "Falha ao cancelar.\n" + exibir_menu_principal()
        if is_back:
            # go back to cancel list
            prev = _restore_prev_state()
            if prev == CANCELAR:
                return processar_mensagem(usuario_id, '')
            return exibir_menu_principal()
        if is_cancel:
            # treat as full abort
            sessoes.pop(usuario_id + '_cancel_target', None)
            sessoes.pop(usuario_id + '_prev_state', None)
            sessoes[usuario_id] = MENU_PRINCIPAL
            return MSG.OPERATION_CANCELLED + "\n" + exibir_menu_principal()

    return "Funcionalidade em desenvolvimento."


# Função para exibir semanas disponíveis
def exibir_semanas_disponiveis(usuario_id):
    return f"{MSG.WEEKS_PROMPT}\n1️⃣ {MSG.WEEK_THIS}\n2️⃣ {MSG.WEEK_NEXT}\n⬅️ {MSG.LABEL_VOLTA}"

# Função para obter dias disponíveis na semana
def obter_dias_disponiveis_semana(semana_offset=0):
    from agenda_service import obter_intervalo_semana_relativa, obter_slots_disponiveis_no_intervalo
    inicio, fim = obter_intervalo_semana_relativa(semana_offset)
    slots = obter_slots_disponiveis_no_intervalo(inicio, fim)
    dias_unicos = sorted(set([slot.date() for slot in slots]))
    return dias_unicos

# Função para exibir dias disponíveis
def exibir_dias_disponiveis(usuario_id, semana_offset=0):
    dias = obter_dias_disponiveis_semana(semana_offset)
    if not dias:
        return MSG.NO_DAYS_AVAILABLE + "\n⬅️ " + MSG.LABEL_VOLTA
    texto = "Escolha o dia:\n"
    for idx, dia in enumerate(dias):
        texto += f"{idx+1}️⃣ {_format_data_pt(dia)}\n"
    texto += f"⬅️ {MSG.LABEL_VOLTA}"
    return texto

# Função para obter horários disponíveis para um dia
def obter_horarios_disponiveis_para_dia(data_dia):
    from agenda_service import obter_slots_disponiveis_para_data
    return obter_slots_disponiveis_para_data(data_dia)

# Função para exibir horários disponíveis
def exibir_horarios_disponiveis(usuario_id, data_dia):
    horarios = obter_horarios_disponiveis_para_dia(data_dia)
    if not horarios:
        return MSG.NO_HOURS_AVAILABLE + "\n⬅️ " + MSG.LABEL_VOLTA
    texto = "Escolha o horário:\n"
    for idx, h in enumerate(horarios):
        texto += f"{idx+1}️⃣ {h.strftime('%H:%M')}\n"
    texto += f"⬅️ {MSG.LABEL_VOLTA}"
    return texto

from agenda_service import registrar_agendamento_google_sheets

# Exemplo de uso (simulação)
if __name__ == "__main__":
    from agenda_service import inicializar_slots_proximos_dias
    print("(Aguarde, preparando agenda de slots disponíveis...)\n")
    inicializar_slots_proximos_dias()
    usuario = 'user1'
    print(exibir_menu_principal())
    while True:
        msg = input('Usuário: ')
        resposta = processar_mensagem(usuario, msg)
        print('Bot:', resposta)
        if resposta == "Até logo!":
            break
