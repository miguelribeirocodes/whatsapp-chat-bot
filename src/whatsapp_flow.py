"""
whatsapp_flow.py
Fluxo principal do chatbot de agendamento via WhatsApp (sem IA).
Menu guiado com opções: Agendar, Reagendar, Cancelar, Sair.
Navegação por datas, horários e confirmação, mantendo integração com agenda_service.py.
"""

from src.agenda_service import *
import re
from src import messages as MSG
import logging

# Imports da refatoração: constantes e helpers
from src.constants import (
    States,
    SessionKeys,
    BUTTON_ID_AGENDAR,
    BUTTON_ID_REAGENDAR,
    BUTTON_ID_CANCELAR,
    BUTTON_ID_VALORES,
    BUTTON_ID_VOLTAR,
    BUTTON_ID_CANCELAR_OPERACAO,
    BUTTON_ID_CONFIRMAR,
    BUTTON_ID_ESTA_SEMANA,
    BUTTON_ID_PROXIMA_SEMANA,
    UniversalActions,
)
from src.flow_helpers import (
    format_data_pt,
    format_appointment_list,
    get_future_appointments,
    is_valid_selection,
    cleanup_agendamento_session,
    cleanup_cancelamento_session,
    build_main_menu,
    build_return_to_menu_message,
)

logger = logging.getLogger(__name__)

# Helper: weekday names in Portuguese (sem "-feira" para consistência visual)
_WEEKDAY_PT = [
    'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'
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

# Simulação de sessão do usuário (em produção, usar banco ou cache)
sessoes = {}

def exibir_menu_principal():
    """
    Retorna uma tupla (texto, items) onde `texto` é a versão em string do menu
    e `items` é uma lista de tuples (id, title, description) pronta para enviar como lista interactive.

    REFATORADO: Agora usa build_main_menu() de flow_helpers.py
    """
    return build_main_menu()

def processar_mensagem(usuario_id, mensagem):
    # Obter estado atual do usuário
    estado = sessoes.get(usuario_id, MENU_PRINCIPAL)

    # Normalizar mensagem para decisões simples
    # Algumas respostas interativas podem chegar como números (int) —
    # garantir que `mensagem` seja sempre string sem espaços para as comparações.
    if mensagem is None:
        mensagem = ""
    else:
        mensagem = str(mensagem).strip()

    texto_normalizado = mensagem.lower()

    # REFATORADO: Usar UniversalActions ao invés de hardcoded
    is_back = UniversalActions.is_back_action(mensagem)
    is_cancel = UniversalActions.is_cancel_action(mensagem)

    # Helper to restore previous state when user backs out from a confirm dialog
    def _restore_prev_state():
        prev_key = SessionKeys.get_user_key(usuario_id, SessionKeys.PREV_STATE)
        prev = sessoes.pop(prev_key, None)
        if prev:
            sessoes[usuario_id] = prev
            return prev
        sessoes[usuario_id] = MENU_PRINCIPAL
        return MENU_PRINCIPAL

    # ========================================================================
    # ESTADO: MENU_PRINCIPAL (REFATORADO)
    # ========================================================================

    # Responder a saudações com o menu principal (inclui cumprimento)
    if estado == MENU_PRINCIPAL and texto_normalizado in ("oi", "olá", "ola", "boa tarde", "bom dia", "boa noite"):
        menu_text, _ = exibir_menu_principal()
        # Se usuário tem nome cadastrado, usa saudação personalizada; senão usa genérica
        primeiro_nome = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.FIRST_NAME))
        if primeiro_nome:
            return f"Olá, {primeiro_nome}!\n{menu_text}"
        else:
            return f"{MSG.WELCOME}\n{menu_text}"

    if estado == MENU_PRINCIPAL:
        # Se o usuário pressionou Voltar/Cancelar mesmo estando no menu principal
        # (por exemplo após um send_back_cancel_buttons), tratar apropriadamente.
        if is_back:
            menu_text, _ = exibir_menu_principal()
            # Retorna apenas o menu sem saudação (evita repetição)
            return menu_text

        if is_cancel:
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

        # Opção 1: Agendar
        if mensagem == BUTTON_ID_AGENDAR:
            sessoes[usuario_id] = AGENDAR
            sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET)] = 0
            return exibir_semanas_disponiveis(usuario_id)

        # Opção 2: Reagendar
        elif mensagem == BUTTON_ID_REAGENDAR:
            sessoes[usuario_id] = REAGENDAR
            return processar_mensagem(usuario_id, '')

        # Opção 3: Cancelar agendamento
        elif mensagem == BUTTON_ID_CANCELAR:
            sessoes[usuario_id] = CANCELAR
            return processar_mensagem(usuario_id, '')

        # Opção 4: Consultar valores e formas de pagamento
        elif mensagem == BUTTON_ID_VALORES:
            # Mantém o usuário no menu principal após exibir as informações
            return f"{MSG.PAYMENT_TITLE}\n{MSG.PAYMENT_INFO}\n"

        # Opção inválida
        else:
            menu_text, _ = exibir_menu_principal()
            return f"{MSG.INVALID_OPTION} Escolha uma das opções abaixo:\n{menu_text}"

    # ========================================================================
    # ESTADO: AGENDAR (REFATORADO - usa constantes e helpers)
    # ========================================================================
    if estado == AGENDAR:
        # Navegação entre semanas
        if is_cancel:
            # Abortar e voltar ao menu principal
            sessoes[usuario_id] = MENU_PRINCIPAL
            # REFATORADO: usa helper de limpeza
            cleanup_agendamento_session(sessoes, usuario_id)
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

        # Opção 1: Esta semana
        if mensagem == BUTTON_ID_ESTA_SEMANA:
            sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET)] = 0
            sessoes[usuario_id] = ESCOLHER_DIA
            return exibir_dias_disponiveis(usuario_id, 0)

        # Opção 2: Próxima semana
        elif mensagem == BUTTON_ID_PROXIMA_SEMANA:
            sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET)] = 1
            sessoes[usuario_id] = ESCOLHER_DIA
            return exibir_dias_disponiveis(usuario_id, 1)

        # Voltar ao menu principal
        elif is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            menu_text, _ = exibir_menu_principal()
            return menu_text

        # Opção inválida
        else:
            return f"{MSG.INVALID_OPTION}. Escolha uma semana:\n{exibir_semanas_disponiveis(usuario_id)}"

    # ========================================================================
    # ESTADO: REAGENDAR (REFATORADO - elimina 40 linhas duplicadas!)
    # ========================================================================
    if estado == REAGENDAR:
        # Primeira entrada: buscar e exibir agendamentos futuros
        if SessionKeys.LISTA_AGENDAMENTOS not in sessoes:
            # REFATORADO: usa helper ao invés de código inline
            agendamentos = get_future_appointments()
            sessoes[SessionKeys.LISTA_AGENDAMENTOS] = agendamentos

            # Sem agendamentos futuros
            if not agendamentos:
                sessoes[usuario_id] = MENU_PRINCIPAL
                return build_return_to_menu_message("Nenhum agendamento futuro encontrado.")

            # REFATORADO: usa helper de formatação
            return format_appointment_list(agendamentos, 'reagendar')

        # Ações de navegação
        if is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS, None)
            menu_text, _ = exibir_menu_principal()
            return menu_text

        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS, None)
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

        # Processar seleção do agendamento
        try:
            idx = int(mensagem) - 1
            agendamentos = sessoes[SessionKeys.LISTA_AGENDAMENTOS]

            # REFATORADO: usa helper de validação
            if is_valid_selection(idx, agendamentos):
                dt, linha = agendamentos[idx]
                sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.REAGENDAR_ANTIGO)] = dt
                sessoes[usuario_id] = AGENDAR
                sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS, None)
                return "Escolha a nova data e horário:\n" + exibir_semanas_disponiveis(usuario_id)
            else:
                # Opção inválida: reexibir lista (SEM DUPLICAÇÃO!)
                return f"{MSG.INVALID_OPTION} {format_appointment_list(agendamentos, 'reagendar')}"

        except (ValueError, KeyError):
            # Erro ao parsear: reexibir lista (SEM DUPLICAÇÃO!)
            agendamentos = sessoes.get(SessionKeys.LISTA_AGENDAMENTOS, [])
            return f"{MSG.INVALID_OPTION} {format_appointment_list(agendamentos, 'reagendar')}"

    # ========================================================================
    # ESTADO: CANCELAR (REFATORADO - elimina 40 linhas duplicadas!)
    # ========================================================================
    if estado == CANCELAR:
        # Primeira entrada: buscar e exibir agendamentos futuros
        if SessionKeys.LISTA_AGENDAMENTOS_CANCELAR not in sessoes:
            # REFATORADO: usa helper ao invés de código inline
            agendamentos = get_future_appointments()
            sessoes[SessionKeys.LISTA_AGENDAMENTOS_CANCELAR] = agendamentos

            # Sem agendamentos futuros
            if not agendamentos:
                sessoes[usuario_id] = MENU_PRINCIPAL
                return build_return_to_menu_message("Nenhum agendamento futuro encontrado.")

            # REFATORADO: usa helper de formatação
            return format_appointment_list(agendamentos, 'cancelar')

        # Ações de navegação
        if is_back:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS_CANCELAR, None)
            menu_text, _ = exibir_menu_principal()
            return menu_text

        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS_CANCELAR, None)
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

        # Processar seleção do agendamento
        try:
            idx = int(mensagem) - 1
            agendamentos = sessoes[SessionKeys.LISTA_AGENDAMENTOS_CANCELAR]

            # REFATORADO: usa helper de validação
            if is_valid_selection(idx, agendamentos):
                dt, linha = agendamentos[idx]
                # Pedir confirmação antes de cancelar
                sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.CANCEL_TARGET)] = dt
                sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.PREV_STATE)] = CANCELAR
                sessoes[usuario_id] = CONFIRM_CANCEL_APPOINTMENT
                # REFATORADO: usa helper de formatação
                return MSG.CONFIRM_CANCEL_APPOINTMENT_TEMPLATE.format(
                    date=format_data_pt(dt),
                    time=dt.strftime('%H:%M')
                )
            else:
                # Opção inválida: reexibir lista (SEM DUPLICAÇÃO!)
                return f"{MSG.INVALID_OPTION} {format_appointment_list(agendamentos, 'cancelar')}"

        except (ValueError, KeyError):
            # Erro ao parsear: reexibir lista (SEM DUPLICAÇÃO!)
            agendamentos = sessoes.get(SessionKeys.LISTA_AGENDAMENTOS_CANCELAR, [])
            return f"{MSG.INVALID_OPTION} {format_appointment_list(agendamentos, 'cancelar')}"

    # ========================================================================
    # ESTADO: ESCOLHER_DIA (REFATORADO - usa constantes e helpers)
    # ========================================================================
    if estado == ESCOLHER_DIA:
        try:
            # Cancelar operação
            if is_cancel:
                sessoes[usuario_id] = MENU_PRINCIPAL
                # REFATORADO: usa helper de limpeza
                cleanup_agendamento_session(sessoes, usuario_id)
                return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

            # Voltar para escolha de semana
            if is_back:
                sessoes[usuario_id] = AGENDAR
                return exibir_semanas_disponiveis(usuario_id)

            # Processar seleção do dia
            dia_idx = int(mensagem) - 1
            semana_offset_key = SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET)
            semana_offset = sessoes.get(semana_offset_key, 0)
            dias = obter_dias_disponiveis_semana(semana_offset)

            # REFATORADO: usa helper de validação
            if is_valid_selection(dia_idx, dias):
                sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.DIA_ESCOLHIDO)] = dias[dia_idx]
                sessoes[usuario_id] = ESCOLHER_HORARIO
                return exibir_horarios_disponiveis(usuario_id, dias[dia_idx])
            else:
                return f"{MSG.INVALID_OPTION}. Escolha um dia:\n{exibir_dias_disponiveis(usuario_id, semana_offset)}"

        except (ValueError, IndexError):
            semana_offset = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET), 0)
            return f"{MSG.INVALID_OPTION}. Escolha um dia:\n{exibir_dias_disponiveis(usuario_id, semana_offset)}"

    # ========================================================================
    # ESTADO: ESCOLHER_HORARIO (REFATORADO - usa constantes e helpers)
    # ========================================================================
    if estado == ESCOLHER_HORARIO:
        try:
            # Cancelar operação
            if is_cancel:
                sessoes[usuario_id] = MENU_PRINCIPAL
                # REFATORADO: usa helper de limpeza
                cleanup_agendamento_session(sessoes, usuario_id)
                return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

            # Voltar para escolha de dia
            if is_back:
                sessoes[usuario_id] = ESCOLHER_DIA
                semana_offset = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.SEMANA_OFFSET), 0)
                return exibir_dias_disponiveis(usuario_id, semana_offset)

            # Processar seleção do horário
            horario_idx = int(mensagem) - 1
            dia_escolhido = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.DIA_ESCOLHIDO))
            horarios = obter_horarios_disponiveis_para_dia(dia_escolhido)

            # REFATORADO: usa helper de validação
            if is_valid_selection(horario_idx, horarios):
                sessoes[SessionKeys.get_user_key(usuario_id, SessionKeys.HORARIO_ESCOLHIDO)] = horarios[horario_idx]
                sessoes[usuario_id] = CONFIRMAR
                # REFATORADO: usa helper de formatação
                return MSG.CONFIRM_AGENDAMENTO_TEMPLATE.format(
                    date=format_data_pt(horarios[horario_idx]),
                    time=horarios[horario_idx].strftime('%H:%M')
                )
            else:
                return f"{MSG.INVALID_OPTION}. Escolha um horário:\n{exibir_horarios_disponiveis(usuario_id, dia_escolhido)}"

        except (ValueError, IndexError):
            dia_escolhido = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.DIA_ESCOLHIDO))
            return f"{MSG.INVALID_OPTION}. Escolha um horário:\n{exibir_horarios_disponiveis(usuario_id, dia_escolhido)}"

    # ========================================================================
    # ESTADO: CONFIRMAR (REFATORADO - mensagens melhoradas!)
    # ========================================================================
    if estado == CONFIRMAR:
        logger.debug('[flow] CONFIRMAR state received mensagem=%s is_cancel=%s', mensagem, is_cancel)

        # Cancelar operação
        if is_cancel:
            sessoes[usuario_id] = MENU_PRINCIPAL
            cleanup_agendamento_session(sessoes, usuario_id)
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

        # Confirmar agendamento
        if mensagem == BUTTON_ID_CONFIRMAR:
            horario = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.HORARIO_ESCOLHIDO))
            nome_paciente = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.FIRST_NAME)) or "Paciente WhatsApp"

            # Detectar se é reagendamento
            reagendar_antigo_key = SessionKeys.get_user_key(usuario_id, SessionKeys.REAGENDAR_ANTIGO)
            is_reagendamento = reagendar_antigo_key in sessoes
            logger.info(f"[confirmacao_agendamento] DEBUG: reagendar_antigo_key={reagendar_antigo_key}, in_sessoes={is_reagendamento}, sessoes_keys={list(sessoes.keys())}")

            # Se for reagendamento, guardar dados do agendamento antigo antes de cancelar
            old_appointment_dt = None
            if is_reagendamento:
                old_appointment_dt = sessoes[reagendar_antigo_key]
                logger.info(f"[confirmacao_agendamento] Reagendamento detectado! old_appointment_dt={old_appointment_dt}")
                from src.agenda_service import cancelar_agendamento_por_data_hora
                cancelar_agendamento_por_data_hora(old_appointment_dt)
                sessoes.pop(reagendar_antigo_key, None)

            # Registrar novo agendamento
            registrar_agendamento_google_sheets(
                nome_paciente=nome_paciente,
                data_hora_consulta=horario,
                origem="whatsapp_simulado",
                telefone=usuario_id,
                observacoes="Agendado via menu bot"
            )

            # Agendar lembretes
            try:
                from src.agenda_service import registrar_lembrete_agendamento
                from src.scheduler import schedule_at
                from datetime import timedelta, datetime

                reminder_dt = horario - timedelta(hours=MSG.REMINDER_HOURS_BEFORE)

                row_idx = None
                try:
                    row_idx = registrar_lembrete_agendamento(
                        horario, reminder_dt, usuario_id, nome_paciente,
                        tipo="patient_reminder", observacoes="Agendado via bot"
                    )
                    print(f"✅ [confirmacao_agendamento] Lembrete registrado na linha {row_idx}")
                    logger.info(f"[confirmacao_agendamento] Lembrete registrado na linha {row_idx}")
                except Exception as e:
                    print(f"🔴 [confirmacao_agendamento] ERRO ao registrar lembrete: {e}")
                    logger.exception(f"[confirmacao_agendamento] ERRO ao registrar lembrete: {e}")
                    row_idx = None

                def _send_and_mark(row=row_idx, phone=usuario_id, dt=horario, patient=nome_paciente):
                    print(f"🟡 [_send_and_mark] Iniciando envio de lembrete: row={row}, phone={phone}, dt={dt}")
                    try:
                        primeiro = (patient or '').split()[0] if patient else ''
                        greeting = f"Olá, {primeiro}!\n" if primeiro else ''
                        appt_text = MSG.REMINDER_TEMPLATE.format(
                            date=dt.strftime('%d/%m/%Y'),
                            time=dt.strftime('%H:%M')
                        )
                        action = MSG.REMINDER_ACTION_PROMPT if hasattr(MSG, 'REMINDER_ACTION_PROMPT') else ''
                        text = greeting + appt_text + ("\n" + action if action else "")
                        print(f"🟡 [_send_and_mark] Enviando lembrete para paciente {phone}")
                        from src import whatsapp_webhook
                        whatsapp_webhook.send_reminder_confirm_buttons(phone, text, dt.isoformat())
                        print(f"✅ [_send_and_mark] Lembrete enviado com sucesso para {phone}")
                        logger.info(f"[_send_and_mark] Lembrete enviado com sucesso para {phone}")
                    except Exception as e:
                        print(f"🔴 [_send_and_mark] ERRO ao enviar lembrete para {phone}: {e}")
                        logger.exception(f'[_send_and_mark] ERRO ao enviar lembrete para {phone}: {e}')

                    # Tentar deletar o lembrete da planilha
                    try:
                        if row:
                            print(f"🟡 [_send_and_mark] Tentando remover lembrete da linha {row}")
                            removed = remover_lembrete_por_row(row)
                            if removed:
                                print(f"✅ [_send_and_mark] Lembrete (linha {row}) removido com SUCESSO")
                                logger.info(f"[_send_and_mark] Lembrete (linha {row}) removido com SUCESSO")
                            else:
                                print(f"🔴 [_send_and_mark] Falha ao remover lembrete (linha {row}) - retornou False")
                                logger.warning(f"[_send_and_mark] Falha ao remover lembrete (linha {row}) - retornou False")
                        else:
                            print(f"🔴 [_send_and_mark] row_idx é None, não removendo lembrete")
                            logger.warning(f"[_send_and_mark] row_idx é None, não removendo lembrete")
                    except Exception as e:
                        print(f"🔴 [_send_and_mark] ERRO ao remover lembrete (linha {row}): {e}")
                        logger.exception(f"[_send_and_mark] ERRO ao remover lembrete (linha {row}): {e}")

                if reminder_dt > datetime.now():
                    print(f"🟡 [confirmacao_agendamento] Agendando lembrete para {reminder_dt}")
                    logger.info(f"[confirmacao_agendamento] Agendando lembrete para {reminder_dt}")
                    schedule_at(reminder_dt, _send_and_mark)
                else:
                    print(f"🟡 [confirmacao_agendamento] Enviando lembrete imediatamente (já passou da hora de agendamento)")
                    logger.info(f"[confirmacao_agendamento] Enviando lembrete imediatamente (já passou da hora de agendamento)")
                    _send_and_mark()

                # Notificar dono da clínica
                try:
                    from src import whatsapp_webhook
                    if is_reagendamento and old_appointment_dt:
                        # Reagendamento: envia mensagem única com dados antigos e novos
                        logger.info(f"[confirmacao_agendamento] Enviando notificacao de REAGENDAMENTO ao dono")
                        whatsapp_webhook.send_reminder_to_owner(
                            patient_name=nome_paciente,
                            date=horario.strftime('%d/%m/%Y'),
                            time=horario.strftime('%H:%M'),
                            isReschedule=True,
                            old_date=old_appointment_dt.strftime('%d/%m/%Y'),
                            old_time=old_appointment_dt.strftime('%H:%M')
                        )
                    elif is_reagendamento and not old_appointment_dt:
                        logger.warning(f"[confirmacao_agendamento] REAGENDAMENTO detectado mas old_appointment_dt eh None!")
                        # Novo agendamento simples como fallback
                        whatsapp_webhook.send_reminder_to_owner(
                            patient_name=nome_paciente,
                            date=horario.strftime('%d/%m/%Y'),
                            time=horario.strftime('%H:%M')
                        )
                    else:
                        # Novo agendamento simples
                        logger.info(f"[confirmacao_agendamento] Enviando notificacao de NOVO AGENDAMENTO ao dono")
                        whatsapp_webhook.send_reminder_to_owner(
                            patient_name=nome_paciente,
                            date=horario.strftime('%d/%m/%Y'),
                            time=horario.strftime('%H:%M')
                        )
                except Exception as e:
                    logger.exception(f"[confirmacao_agendamento] Erro ao notificar dono: {e}")
            except Exception:
                pass

            # Limpar sessão e voltar ao menu
            sessoes[usuario_id] = MENU_PRINCIPAL
            cleanup_agendamento_session(sessoes, usuario_id)

            # REFATORADO: Mensagem de confirmação melhorada!
            nome_para_msg = nome_paciente.split()[0] if nome_paciente else nome_paciente

            if is_reagendamento:
                # Mensagem específica para reagendamento
                msg_confirmacao = MSG.REAGENDAMENTO_CONFIRMADO.format(
                    date=format_data_pt(horario),
                    time=horario.strftime('%H:%M')
                )
            else:
                # Mensagem específica para agendamento novo
                msg_confirmacao = MSG.AGENDAMENTO_CONFIRMADO_FULL.format(
                    date=format_data_pt(horario),
                    time=horario.strftime('%H:%M'),
                    name=nome_para_msg
                )

            return build_return_to_menu_message(msg_confirmacao)

        # Voltar para escolha de horário
        elif is_back:
            sessoes[usuario_id] = ESCOLHER_HORARIO
            dia_escolhido = sessoes.get(SessionKeys.get_user_key(usuario_id, SessionKeys.DIA_ESCOLHIDO))
            return exibir_horarios_disponiveis(usuario_id, dia_escolhido)

        # Opção inválida
        else:
            return f"{MSG.INVALID_OPTION} Confirme ou volte:\n1️⃣ Confirmar\n⬅️ {MSG.LABEL_VOLTA}"

    # Nota: confirmação genérica de cancelar removida; cancelamentos de operação agora abortam imediatamente

    # ========================================================================
    # ESTADO: CONFIRM_CANCEL_APPOINTMENT (REFATORADO - mensagem melhorada!)
    # ========================================================================
    if estado == CONFIRM_CANCEL_APPOINTMENT:
        logger.debug('[flow] CONFIRM_CANCEL_APPOINTMENT state received mensagem=%s is_cancel=%s', mensagem, is_cancel)

        # Confirmar cancelamento
        if mensagem == BUTTON_ID_CONFIRMAR:
            cancel_target_key = SessionKeys.get_user_key(usuario_id, SessionKeys.CANCEL_TARGET)
            dt = sessoes.pop(cancel_target_key, None)

            # tentar obter o nome do paciente associado (antes de cancelar)
            nome_para_notif = None
            try:
                if dt is not None:
                    ags = get_future_appointments()
                    for adt, linha in ags:
                        if adt == dt:
                            nome_para_notif = (linha[3] if len(linha) > 3 else None) or ''
                            break
            except Exception:
                nome_para_notif = None

            from src.agenda_service import cancelar_agendamento_por_data_hora
            sucesso = False
            if dt:
                sucesso = cancelar_agendamento_por_data_hora(dt)

            # Limpar sessão
            sessoes.pop(SessionKeys.get_user_key(usuario_id, SessionKeys.PREV_STATE), None)
            sessoes.pop(SessionKeys.LISTA_AGENDAMENTOS_CANCELAR, None)
            sessoes[usuario_id] = MENU_PRINCIPAL

            if sucesso:
                # REFATORADO: Mensagem de cancelamento melhorada!
                msg_cancelamento = MSG.CANCEL_SUCCESS_TEMPLATE.format(
                    date=format_data_pt(dt),
                    time=dt.strftime('%H:%M')
                )
                try:
                    logger.info(f"[confirmacao_cancelamento] Enviando notificacao de CANCELAMENTO ao dono")
                    from src import whatsapp_webhook
                    whatsapp_webhook.send_reminder_to_owner(
                        nome_para_notif or "",
                        dt.strftime('%d/%m/%Y') if dt else '',
                        dt.strftime('%H:%M') if dt else '',
                        isCancel=True
                    )
                except Exception as e:
                    logger.exception(f"[confirmacao_cancelamento] Erro ao notificar dono: {e}")
                return build_return_to_menu_message(msg_cancelamento)
            else:
                return build_return_to_menu_message("Falha ao cancelar.")

        # Voltar para lista de agendamentos
        if is_back:
            prev = _restore_prev_state()
            if prev == CANCELAR:
                return processar_mensagem(usuario_id, '')
            menu_text, _ = exibir_menu_principal()
            return menu_text

        # Cancelar a operação de cancelamento (abortar)
        if is_cancel:
            sessoes.pop(SessionKeys.get_user_key(usuario_id, SessionKeys.CANCEL_TARGET), None)
            sessoes.pop(SessionKeys.get_user_key(usuario_id, SessionKeys.PREV_STATE), None)
            sessoes[usuario_id] = MENU_PRINCIPAL
            return build_return_to_menu_message(MSG.OPERATION_CANCELLED)

    # Para entradas desconhecidas, reexibir o menu principal (loop amigável)
    menu_text, _ = exibir_menu_principal()
    return menu_text


# Função para exibir semanas disponíveis
def exibir_semanas_disponiveis(usuario_id):
    return f"{MSG.WEEKS_PROMPT}\n1️⃣ {MSG.WEEK_THIS}\n2️⃣ {MSG.WEEK_NEXT}\n⬅️ {MSG.LABEL_VOLTA}"

# Função para obter dias disponíveis na semana
def obter_dias_disponiveis_semana(semana_offset=0):
    from src.agenda_service import obter_intervalo_semana_relativa, obter_slots_disponiveis_no_intervalo
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
    from src.agenda_service import obter_slots_disponiveis_para_data
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

from src.agenda_service import registrar_agendamento_google_sheets

# Exemplo de uso (simulação)
if __name__ == "__main__":
    from src.agenda_service import inicializar_slots_proximos_dias
    print("(Aguarde, preparando agenda de slots disponíveis...)\n")
    inicializar_slots_proximos_dias()
    usuario = 'user1'
    print(exibir_menu_principal()[0])
    while True:
        msg = input('Usuário: ')
        resposta = processar_mensagem(usuario, msg)
        print('Bot:', resposta)
        if resposta == "Até logo!":
            break
