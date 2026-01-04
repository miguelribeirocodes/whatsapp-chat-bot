from fastapi import FastAPI, Request, HTTPException, Response  # importa FastAPI e tipos Request/HTTPException/Response
import os  # importa módulo para variáveis de ambiente
import requests  # importa requests para chamadas HTTP à Graph API
from dotenv import load_dotenv  # importa load_dotenv para carregar .env
import logging  # importa logging para logs
import json  # importa json para serializar payloads de debug
from datetime import datetime, timezone, timedelta  # tipos de data/hora
from src.logging_config import setup_logging  # importa configuração centralizada de logging

setup_logging()  # configura logging com handlers de console e arquivo
logger = logging.getLogger(__name__)  # obtém logger do módulo

# Timezone do Brasil (GMT-3) - importante para servidor em UTC
BRAZIL_TZ_OFFSET = timedelta(hours=-3)

def agora_brasil() -> datetime:
    """Retorna o horário atual no fuso horário do Brasil (GMT-3)."""
    utc_now = datetime.now(timezone.utc)
    brazil_now = utc_now + BRAZIL_TZ_OFFSET
    return brazil_now.replace(tzinfo=None)
from src.agenda_service import (
    buscar_perfil_por_telefone,
    criar_cadastro_paciente,
    remover_lembrete_por_row,
    remover_lembretes_por_appointment,
    obter_lembretes_pendentes,
)


# Helpers para nomes dos dias da semana em português (usados nos títulos/descrições)
def _abbr_weekday(idx: int) -> str:  # retorna abreviação do dia da semana em PT
    return ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][idx]  # valores abreviados

def _full_weekday(idx: int) -> str:  # retorna o nome completo do dia da semana em PT (sem "-feira" para consistência)
    return ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'][idx]  # valores sem "-feira"

load_dotenv()  # carrega variáveis de ambiente de um arquivo .env quando presente

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # token do WhatsApp Cloud
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")  # id do telefone/container
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")  # token de verificação para webhook
GRAPH_API_BASE = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"  # endpoint da Graph API

from src import whatsapp_flow as wf  # importa lógica do fluxo conversacional (módulo local)
from src import messages as MSG
from src import scheduler
from src import ngrok_service  # Auto-inicia ngrok se NGROK_ENABLED=true

app = FastAPI()  # instancia FastAPI

# Log URL do ngrok se habilitado
if ngrok_service.is_enabled():
    tunnel_url = ngrok_service.get_tunnel_url()
    if tunnel_url:
        logger.info('[startup] Ngrok tunnel: %s/webhook', tunnel_url)

# -------------------------------------------------------
# Inicialização de slots na startup
# -------------------------------------------------------
try:
    from src.agenda_service import inicializar_slots_proximos_dias, NUM_DIAS_GERAR_SLOTS
    logger.info('[startup] Inicializando slots para os próximos %d dias...', NUM_DIAS_GERAR_SLOTS)
    inicializar_slots_proximos_dias()
    logger.info('[startup] Slots inicializados com sucesso!')
except Exception:
    logger.exception('[startup] Falha ao inicializar slots na agenda')


def send_text(to: str, text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers para autorização e content-type
    payload = {  # payload JSON para mensagem de texto
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    try:
        logger.info("[send_text] Sending to %s", to)  # log simples do destino
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # chama a Graph API
        if r.status_code != 200:
            logger.error("[send_text] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_text] Successfully sent to %s", to)  # log de sucesso
        return r  # retorna o response para o chamador
    except Exception as e:
        logger.exception("[send_text] Exception while sending message to %s", to)  # log de exceção com destino
        raise  # re-levanta exceção para tratamento externo


def send_reminder(to: str, text: str):
    """Wrapper to send reminder messages (reuses send_text). Kept as a single place to extend later."""
    try:
        logger.info("[send_reminder] Sending reminder to %s text=%s", to, text)
        return send_text(to, text)
    except Exception:
        logger.exception("[send_reminder] Failed to send reminder to %s", to)
        raise


def send_reminder_to_owner(patient_name: str, date: str, time: str, isCancel: bool = False,
                           isReschedule: bool = False, old_date: str = None, old_time: str = None):
    """
    Send notification to clinic owner if configured in messages.py

    Args:
        patient_name: Nome do paciente
        date: Data do agendamento (novo, ou do cancelamento)
        time: Horário do agendamento (novo, ou do cancelamento)
        isCancel: Se True, envia mensagem de cancelamento
        isReschedule: Se True, envia mensagem de reagendamento (requer old_date e old_time)
        old_date: Data do agendamento anterior (usado apenas em reagendamento)
        old_time: Horário do agendamento anterior (usado apenas em reagendamento)
    """
    owner = MSG.CLINIC_OWNER_PHONE
    if not owner:
        print("🔴 [send_reminder_to_owner] CLINIC_OWNER_PHONE NÃO está configurado em messages.py! Pulando notificação para dono")
        logger.warning("[send_reminder_to_owner] CLINIC_OWNER_PHONE not configured in messages.py; skipping owner notification")
        return None

    print(f"🟡 [send_reminder_to_owner] Preparando notificacao para dono: phone={owner}, patient={patient_name}, date={date}, time={time}, isCancel={isCancel}, isReschedule={isReschedule}")

    try:
        if isReschedule and old_date and old_time:
            # Reagendamento: mensagem única com info antiga e nova
            text = MSG.OWNER_REMINDER_RESCHEDULE_TEMPLATE.format(
                patient=patient_name,
                old_date=old_date,
                old_time=old_time,
                new_date=date,
                new_time=time
            )
            print(f"🟡 [send_reminder_to_owner] Tipo: REAGENDAMENTO")
        elif isCancel:
            # Cancelamento simples
            text = MSG.OWNER_REMINDER_CANCEL_TEMPLATE.format(
                patient=patient_name,
                date=date,
                time=time
            )
            print(f"🟡 [send_reminder_to_owner] Tipo: CANCELAMENTO")
        else:
            # Novo agendamento
            text = MSG.OWNER_REMINDER_TEMPLATE.format(
                patient=patient_name,
                date=date,
                time=time
            )
            print(f"🟡 [send_reminder_to_owner] Tipo: NOVO AGENDAMENTO")

        print(f"🟡 [send_reminder_to_owner] Enviando para {owner}...")
        result = send_text(owner, text)
        print(f"✅ [send_reminder_to_owner] Notificacao enviada com SUCESSO para {owner}")
        logger.info("[send_reminder_to_owner] Notificacao enviada com sucesso para %s", owner)
        return result
    except Exception as e:
        print(f"🔴 [send_reminder_to_owner] ERRO ao notificar dono {owner}: {str(e)}")
        logger.exception("[send_reminder_to_owner] ERRO ao notificar dono %s: %s", owner, str(e))
        return None


# Schedule daily summary for owner at configured hour
try:
    _owner_summary_sent_dates = set()

    def _owner_daily_summary():
        try:
            from src.agenda_service import obter_todos_agenda_cached
            todos = obter_todos_agenda_cached()[1:]
            hoje_dt = agora_brasil()  # Usa horário do Brasil
            hoje = hoje_dt.strftime('%d/%m/%Y')
            if hoje in _owner_summary_sent_dates:
                logger.info('[daily_summary] already sent for %s, skipping', hoje)
                return
            linhas = [l for l in todos if len(l) >= 6 and l[1].strip() == hoje and l[5].strip().upper() == 'AGENDADO']
            owner = MSG.CLINIC_OWNER_PHONE
            if not owner:
                logger.info('[daily_summary] no owner configured, skipping')
                return
            if not linhas:
                logger.info('[daily_summary] no appointments for %s', hoje)
                # Send an explicit message to the owner stating there are no appointments today
                try:
                    send_text(owner, f"Não há agendamentos para hoje ({hoje}).")
                except Exception:
                    logger.exception('[daily_summary] failed sending empty summary to owner')
                _owner_summary_sent_dates.add(hoje)
                return
            # build summary text
            texto = f"Agendamentos para hoje ({hoje}):\n"
            for ln in linhas:
                hora = ln[2].strip()
                paciente = ln[3].strip() or 'Paciente'
                telefone = ln[4].strip() or ''
                texto += f"- {hora} {paciente} {telefone}\n"
            send_text(owner, texto)
            _owner_summary_sent_dates.add(hoje)
        except Exception:
            logger.exception('[daily_summary] error while building owner summary')

    # schedule first daily run
    schedule_hour = int(getattr(MSG, 'OWNER_DAILY_SUMMARY_HOUR', 7))
    scheduler.schedule_daily(schedule_hour, 0, _owner_daily_summary)

    # If current time is past scheduled hour and today's summary not yet sent, send it now
    try:
        now = agora_brasil()  # Usa horário do Brasil
        if now.hour >= schedule_hour:
            hoje = now.strftime('%d/%m/%Y')
            if hoje not in _owner_summary_sent_dates:
                logger.info('[daily_summary] current time past schedule hour, sending today summary now')
                _owner_daily_summary()
    except Exception:
        logger.exception('[daily_summary] error when checking immediate send')
except Exception:
    logger.exception('[webhook] Failed to schedule daily owner summary')

# Schedule daily slot creation to maintain rolling window
try:
    _daily_slots_created_dates = set()

    def _daily_add_future_slots():
        """
        Adiciona slots para o dia que está NUM_DIAS_GERAR_SLOTS dias no futuro.
        Mantém janela deslizante de slots disponíveis.
        """
        try:
            from src.agenda_service import adicionar_slots_dia_futuro
            hoje = agora_brasil().strftime('%d/%m/%Y')  # Usa horário do Brasil

            if hoje in _daily_slots_created_dates:
                logger.info('[daily_slots] slots already created for %s, skipping', hoje)
                return

            logger.info('[daily_slots] Adding future slots for rolling window...')
            adicionar_slots_dia_futuro()
            _daily_slots_created_dates.add(hoje)
            logger.info('[daily_slots] Future slots added successfully')
        except Exception:
            logger.exception('[daily_slots] error while adding future slots')

    # Agendar para rodar à meia-noite todos os dias (00:01)
    scheduler.schedule_daily(0, 1, _daily_add_future_slots)

    # Se já passou da meia-noite e ainda não rodou hoje, rodar agora
    try:
        now = agora_brasil()  # Usa horário do Brasil
        hoje = now.strftime('%d/%m/%Y')
        if hoje not in _daily_slots_created_dates:
            logger.info('[daily_slots] Running initial slot creation for today')
            _daily_add_future_slots()
    except Exception:
        logger.exception('[daily_slots] error when checking immediate slot creation')
except Exception:
    logger.exception('[webhook] Failed to schedule daily slot creation')

# (startup pending reminders logic is executed after helper functions are defined)


def send_menu_buttons(to: str, text: str, items: list = None):
    # Envia o menu principal como uma única lista interativa com 4 opções.
    # `items` (opcional) deve ser uma lista de tuples (id, title, description).
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}

    # O header de uma lista tem limite de 60 caracteres; usamos apenas a primeira
    # linha do `text` como header. Se essa primeira linha exceder 60 chars,
    # enviaremos a mensagem completa como texto e usaremos um header curto
    # e neutro para a lista para evitar duplicação visual.
    header_text = ''
    try:
        if isinstance(text, str):
            # escolher apenas a primeira linha para o header
            header_text = text.split('\n', 1)[0].strip() or ''
        if not header_text:
            header_text = MSG.MENU_LIST_TITLE
        if len(header_text) > 60:
            try:
                # enviar a mensagem completa como texto (cumprimento + prompt)
                send_text(to, text)
            except Exception:
                logger.exception('[send_menu_buttons] falha ao enviar texto longo antes da lista')
            # usar um header curto e neutro para a lista (evita repetir o cumprimento)
            header_text = MSG.MENU_LIST_TITLE
    except Exception:
        header_text = MSG.MENU_LIST_TITLE

    # Determina o corpo (body) da lista interativa. Se o `text` contiver múltiplas
    # linhas (ex: cumpriment0 + MENU_PROMPT + LIST_BODY_TEXT), usamos a parte
    # após a primeira quebra de linha como corpo para preservar o prompt.
    body_text = MSG.LIST_BODY_TEXT
    try:
        if isinstance(text, str):
            if '\n' in text:
                body_text = text.split('\n', 1)[1].strip() or MSG.LIST_BODY_TEXT
            else:
                # se não houver quebra, use o próprio texto (se não vazio)
                body_text = text.strip() or MSG.LIST_BODY_TEXT
    except Exception:
        body_text = MSG.LIST_BODY_TEXT

    sections = [{"title": MSG.MENU_LIST_TITLE, "rows": []}]
    # rows: id, title, description — use `items` se fornecido, caso contrário use padrão
    if items and isinstance(items, list):
        rows = items
    else:
        rows = [
            ("1", MSG.MENU_AGENDAR, ""),
            ("2", MSG.MENU_REAGENDAR, ""),
            ("3", MSG.MENU_CANCELAR, ""),
            ("4", MSG.MENU_VALORES, ""),
        ]
    for id_, title, desc in rows:
        sections[0]["rows"].append({"id": id_, "title": title, "description": desc})

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
            "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header_text},
            "body": {"text": body_text},
            "action": {"button": MSG.LIST_BUTTON_LABEL, "sections": sections}
        }
    }
    try:
        logger.info("[send_menu_buttons] Sending to %s", to)  # log simples do destino
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia para Graph API
        if r.status_code != 200:
            logger.error("[send_menu_buttons] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_menu_buttons] Successfully sent to %s", to)  # log de sucesso
        return r  # retorna response
    except Exception:
        logger.exception("[send_menu_buttons] Exception while sending buttons to %s", to)  # log de erro com destino
        raise  # re-levanta


def send_weeks_buttons(to: str, text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers
    # botões de seleção de semana em português
    payload = {  # payload interativo com opções de semana
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
                "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "1", "title": MSG.WEEK_THIS}},
                    {"type": "reply", "reply": {"id": "2", "title": MSG.WEEK_NEXT}},
                    {"type": "reply", "reply": {"id": "0", "title": MSG.LABEL_VOLTA}}
                ]
            }
        }
    }
    try:
        logger.info("[send_weeks_buttons] Sending to %s", to)  # log simples do destino
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        if r.status_code != 200:
            logger.error("[send_weeks_buttons] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_weeks_buttons] Successfully sent to %s", to)  # log de sucesso
        return r
    except Exception:
        logger.exception("[send_weeks_buttons] Exception while sending week buttons to %s", to)  # log de erro com destino
        raise


def send_list_days(to: str, title: str, items: list):
    # items: list of tuples (id, title, description)
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers
    sections = [{"title": MSG.LIST_SECTION_TITLE, "rows": []}]  # cria seção principal da lista
    for id_, t, desc in items:  # percorre itens e adiciona como linhas
        # títulos e descrições em português
        sections[0]["rows"].append({"id": id_, "title": t, "description": desc})  # adiciona row à seção

    payload = {  # payload para tipo list da API
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": title},
            "body": {"text": MSG.LIST_BODY_TEXT},
            "action": {"button": MSG.LIST_BUTTON_LABEL, "sections": sections}
        }
    }
    try:
        logger.info("[send_list_days] Sending to %s payload header=%s rows=%d", to, title, sum(len(s.get('rows',[])) for s in payload['interactive']['action']['sections']))  # log com número de rows
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia para Graph API
        if r.status_code != 200:
            logger.error("[send_list_days] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_list_days] Successfully sent to %s", to)  # log de sucesso
        return r  # retorna response
    except Exception:
        logger.exception("[send_list_days] Exception while sending list of days to %s", to)  # log de erro com destino
        raise  # re-levanta


def send_list_times(to: str, title: str, items: list):
    return send_list_days(to, title, items)  # wrapper que reutiliza send_list_days para horários


def send_confirm_buttons(to: str, text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers
    payload = {  # payload com botões de confirmar/voltar/cancelar
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                    "buttons": [
                    {"type": "reply", "reply": {"id": "1", "title": MSG.LABEL_CONFIRM}},
                    {"type": "reply", "reply": {"id": "0", "title": MSG.LABEL_VOLTA}},
                    {"type": "reply", "reply": {"id": "9", "title": MSG.LABEL_CANCEL}}
                ]
            }
        }
    }
    try:
        logger.info("[send_confirm_buttons] Sending to %s", to)  # log simples do destino
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        if r.status_code != 200:
            logger.error("[send_confirm_buttons] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_confirm_buttons] Successfully sent to %s", to)  # log de sucesso
        return r  # retorna response
    except Exception:
        logger.exception("[send_confirm_buttons] Exception while sending confirm buttons to %s", to)  # log de erro com destino
        raise  # re-levanta


def send_reminder_confirm_buttons(to: str, text: str, appointment_iso: str):
    """Sends confirm buttons for a reminder with custom ids encoding the appointment ISO datetime."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    confirm_id = f"rem_confirm|{appointment_iso}"
    cancel_id = f"rem_cancel|{appointment_iso}"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": confirm_id, "title": MSG.LABEL_CONFIRM}},
                    {"type": "reply", "reply": {"id": cancel_id, "title": MSG.LABEL_CANCEL}}
                ]
            }
        }
    }
    try:
        logger.info("[send_reminder_confirm_buttons] Sending to %s", to)
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            logger.error("[send_reminder_confirm_buttons] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)
        else:
            logger.info("[send_reminder_confirm_buttons] Successfully sent to %s", to)
        return r
    except Exception:
        logger.exception("[send_reminder_confirm_buttons] Exception while sending reminder confirm buttons to %s", to)
        raise


def send_back_cancel_buttons(to: str, text: str = 'Deseja voltar ou cancelar?'):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers
    payload = {  # payload com botões Voltar e Cancelar
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "0", "title": MSG.LABEL_VOLTA}},  # voltar
                    {"type": "reply", "reply": {"id": "9", "title": MSG.LABEL_CANCEL}}  # cancelar
                ]
            }
        }
    }
    try:
        logger.info("[send_back_cancel_buttons] Sending to %s", to)  # log simples do destino
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        if r.status_code != 200:
            logger.error("[send_back_cancel_buttons] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)  # log detalhado em caso de erro
        else:
            logger.info("[send_back_cancel_buttons] Successfully sent to %s", to)  # log de sucesso
        return r  # retorna response
    except Exception:
        logger.exception("[send_back_cancel_buttons] Exception while sending back/cancel buttons to %s", to)  # log de erro com destino
        raise  # re-levanta


def send_back_only_button(to: str, text: str = 'Voltar'):
    """Envia um único botão 'Voltar' (id '0')."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "0", "title": MSG.LABEL_VOLTA}}
                ]
            }
        }
    }
    try:
        logger.info("[send_back_only_button] Sending to %s", to)
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            logger.error("[send_back_only_button] Error sending to %s - Status: %s | Payload: %s | Response: %s",
                        to, r.status_code, json.dumps(payload, ensure_ascii=False), r.text)
        else:
            logger.info("[send_back_only_button] Successfully sent to %s", to)
        return r
    except Exception:
        logger.exception("[send_back_only_button] Exception while sending back-only button to %s", to)
        raise


# On startup, load pending reminders from sheet and schedule/send them
try:
    from src.agenda_service import obter_lembretes_pendentes
    from datetime import datetime
    pendentes = obter_lembretes_pendentes()  # all pending
    for lemb in pendentes:
        sched = lemb['scheduled_dt']
        row = lemb['row']
        telefone = lemb['telefone']
        paciente = lemb['paciente']
        ag_dt = datetime.fromisoformat(lemb['appointment_iso']) if lemb.get('appointment_iso') else None
        if sched <= agora_brasil():  # Usa horário do Brasil
            # send immediately (interactive confirm) and mark
            print(f"🟡 [startup] Enviando lembrete IMEDIATAMENTE (ja passou da hora): row={row}, phone={telefone}, date={lemb['appointment_date']}, time={lemb['appointment_time']}")
            logger.info('[startup] Enviando lembrete IMEDIATAMENTE (ja passou da hora): row=%s, phone=%s, date=%s, time=%s', row, telefone, lemb['appointment_date'], lemb['appointment_time'])
            try:
                # try to personalize using cadastro
                try:
                    perfil = buscar_perfil_por_telefone(telefone)
                    primeiro = (perfil.get('nome') or '').split()[0] if perfil and perfil.get('nome') else ''
                except Exception:
                    primeiro = ''
                greeting = f"Olá, {primeiro}!\n" if primeiro else ''
                appt_text = MSG.REMINDER_TEMPLATE.format(date=lemb['appointment_date'], time=lemb['appointment_time'])
                action = MSG.REMINDER_ACTION_PROMPT if hasattr(MSG, 'REMINDER_ACTION_PROMPT') else ''
                text = greeting + appt_text + ("\n" + action if action else "")
                print(f"🟡 [startup] Enviando lembrete para paciente {telefone}")
                send_reminder_confirm_buttons(telefone, text, lemb['appointment_iso'])
                print(f"✅ [startup] Lembrete enviado com sucesso para {telefone}")
                logger.info('[startup] Lembrete enviado com sucesso para %s', telefone)
            except Exception as e:
                print(f"🔴 [startup] ERRO ao enviar lembrete imediato row={row} phone={telefone}: {str(e)}")
                logger.exception('[startup] ERRO ao enviar lembrete imediato row=%s phone=%s: %s', row, telefone, str(e))
            try:
                # remove the reminder row after sending
                print(f"🟡 [startup] Tentando remover lembrete da linha {row}")
                removed = remover_lembrete_por_row(row)
                if removed:
                    print(f"✅ [startup] Lembrete (linha {row}) removido com SUCESSO")
                    logger.info('[startup] Lembrete (linha %s) removido com SUCESSO', row)
                else:
                    print(f"🔴 [startup] Falha ao remover lembrete (linha {row}) - retornou False")
                    logger.warning('[startup] Falha ao remover lembrete (linha %s) - retornou False', row)
            except Exception as e:
                print(f"🔴 [startup] ERRO ao remover lembrete da linha {row}: {str(e)}")
                logger.exception('[startup] ERRO ao remover lembrete da linha %s: %s', row, str(e))
        else:
            # schedule for future
            try:
                from src.scheduler import schedule_at
                def _send_and_mark_start(row=row, phone=telefone, date_text=lemb['appointment_date'], time_text=lemb['appointment_time'], appt_iso=lemb.get('appointment_iso')):
                    print(f"🟡 [startup._send_and_mark_start] Iniciando envio de lembrete agendado: row={row}, phone={phone}, date={date_text}, time={time_text}")
                    logger.info('[startup._send_and_mark_start] Iniciando envio de lembrete agendado: row=%s, phone=%s, date=%s, time=%s', row, phone, date_text, time_text)
                    try:
                        # lookup perfil at runtime to personalize
                        try:
                            perfil = buscar_perfil_por_telefone(phone)
                            primeiro = (perfil.get('nome') or '').split()[0] if perfil and perfil.get('nome') else ''
                        except Exception:
                            primeiro = ''
                        greeting = f"Olá, {primeiro}!\n" if primeiro else ''
                        appt_text = MSG.REMINDER_TEMPLATE.format(date=date_text, time=time_text)
                        action = MSG.REMINDER_ACTION_PROMPT if hasattr(MSG, 'REMINDER_ACTION_PROMPT') else ''
                        texto = greeting + appt_text + ("\n" + action if action else "")
                        print(f"🟡 [startup._send_and_mark_start] Enviando lembrete para paciente {phone}")
                        send_reminder_confirm_buttons(phone, texto, appt_iso)
                        print(f"✅ [startup._send_and_mark_start] Lembrete enviado com sucesso para {phone}")
                        logger.info('[startup._send_and_mark_start] Lembrete enviado com sucesso para %s', phone)
                    except Exception as e:
                        print(f"🔴 [startup._send_and_mark_start] ERRO ao enviar lembrete agendado row={row} phone={phone}: {str(e)}")
                        logger.exception('[startup._send_and_mark_start] ERRO ao enviar lembrete agendado row=%s phone=%s: %s', row, phone, str(e))
                    try:
                        print(f"🟡 [startup._send_and_mark_start] Tentando remover lembrete da linha {row}")
                        removed = remover_lembrete_por_row(row)
                        if removed:
                            print(f"✅ [startup._send_and_mark_start] Lembrete (linha {row}) removido com SUCESSO")
                            logger.info('[startup._send_and_mark_start] Lembrete (linha %s) removido com SUCESSO', row)
                        else:
                            print(f"🔴 [startup._send_and_mark_start] Falha ao remover lembrete (linha {row}) - retornou False")
                            logger.warning('[startup._send_and_mark_start] Falha ao remover lembrete (linha %s) - retornou False', row)
                    except Exception as e:
                        print(f"🔴 [startup._send_and_mark_start] ERRO ao remover lembrete da linha {row}: {str(e)}")
                        logger.exception('[startup._send_and_mark_start] ERRO ao remover lembrete da linha %s: %s', row, str(e))
                schedule_at(sched, _send_and_mark_start)
            except Exception:
                logger.exception('[startup] failed to schedule pending reminder row=%s', row)
except Exception:
    logger.exception('[startup] error loading pending reminders')


@app.get('/webhook')
async def verify(request: Request):
    params = dict(request.query_params)  # converte query params para dict
    mode = params.get('hub.mode') or params.get('hub.mode')  # lê modo de submissão
    challenge = params.get('hub.challenge')  # obtém challenge enviado pelo Facebook
    token = params.get('hub.verify_token') or params.get('hub.verify_token')  # lê verify token

    # Log EXTREMAMENTE detalhado para debug
    logger.info(f"[webhook-verify] ===== FULL REQUEST DEBUG =====")
    logger.info(f"[webhook-verify] All params: {params}")
    logger.info(f"[webhook-verify] Query string: {request.url.query}")
    logger.info(f"[webhook-verify] mode={repr(mode)}, token={repr(token)}, challenge={repr(challenge)}")
    logger.info(f"[webhook-verify] VERIFY_TOKEN expected={repr(VERIFY_TOKEN)}")
    logger.info(f"[webhook-verify] Token match: {token == VERIFY_TOKEN}")
    logger.info(f"[webhook-verify] Mode match: {mode == 'subscribe'}")

    if mode == 'subscribe' and token == VERIFY_TOKEN:  # valida token recebido
        logger.info(f"[webhook-verify] ✅ SUCCESS - returning challenge={repr(challenge)}")
        return Response(content=challenge, media_type="text/plain")  # retorna challenge como plain text

    logger.warning(f"[webhook-verify] ❌ FAILED - Expected mode='subscribe' and token={repr(VERIFY_TOKEN)}")
    raise HTTPException(status_code=403, detail='Verification failed')  # se inválido, retorna 403


@app.post('/webhook')
async def webhook(request: Request):
    data = await request.json()  # lê corpo JSON da requisição
    try:
        logger.info("[webhook] Incoming POST payload keys=%s", list(data.keys()))  # log das chaves do payload
    except Exception:
        logger.info("[webhook] Incoming POST (unable to summarize payload)")  # fallback de log
    # Parse incoming message(s)
    entries = data.get('entry', [])  # extrai lista de entries do payload
    for entry in entries:  # itera cada entry do webhook
        changes = entry.get('changes', [])  # obtém a lista de changes
        for change in changes:  # itera mudanças
            value = change.get('value', {})  # obtém o objeto value
            messages = value.get('messages', [])  # extrai mensagens (se houver)
            if not messages:  # pula quando não há mensagens
                continue
            for msg in messages:  # itera cada mensagem presente
                from_number = msg.get('from')  # número do remetente
                logger.info("[webhook] Message from=%s type=%s", from_number, msg.get('type'))  # log remetente e tipo
                # Determine payload text to feed into processar_mensagem
                texto = None  # valor padronizado que será passado para o fluxo
                # interactive replies (button or list)
                if msg.get('type') == 'interactive':  # quando for reply interativo
                    inter = msg.get('interactive', {})  # parte interactive do payload
                    itype = inter.get('type')  # tipo de interativo
                    if itype == 'button_reply':  # resposta por botão
                        texto = inter.get('button_reply', {}).get('id')  # id do reply
                        # intercept reminder-specific reply ids
                        if isinstance(texto, str) and texto.startswith('rem_'):
                            try:
                                parts = texto.split('|', 1)
                                action = parts[0]  # rem_confirm / rem_cancel / rem_back
                                app_iso = parts[1] if len(parts) > 1 else None
                            except Exception:
                                action = None
                                app_iso = None
                            # handle reminder actions immediately
                            if action in ('rem_confirm', 'rem_cancel') and app_iso:
                                try:
                                    from src.agenda_service import cancelar_agendamento_por_data_hora, obter_lembretes_pendentes
                                    from datetime import datetime
                                    if action == 'rem_confirm':
                                        # acknowledge confirmation (personalized)
                                        try:
                                            perfil = buscar_perfil_por_telefone(from_number)
                                            primeiro = (perfil.get('nome') or '').split()[0] if perfil and perfil.get('nome') else ''
                                        except Exception:
                                            primeiro = ''
                                        try:
                                            send_text(from_number, MSG.REMINDER_CONFIRMED_MSG.format(name=primeiro))
                                        except Exception:
                                            logger.exception('[rem_handler] failed sending confirmation message')
                                        # remove any matching lembretes for this appointment
                                        try:
                                            remover_lembretes_por_appointment(app_iso, from_number)
                                        except Exception:
                                            logger.exception('[rem_handler] failed removing lembretes for appointment')
                                        # handled — continue to next message
                                        continue
                                    elif action == 'rem_cancel':
                                        try:
                                            dt = datetime.fromisoformat(app_iso)
                                        except Exception:
                                            dt = None
                                        cancelled = False
                                        if dt:
                                            try:
                                                cancelled = cancelar_agendamento_por_data_hora(dt, telefone_esperado=from_number)
                                            except Exception:
                                                logger.exception('[rem_handler] fail cancel')
                                        if cancelled:
                                            send_text(from_number, MSG.REMINDER_CANCELLED_MSG)
                                            # Notificar dono sobre o cancelamento via reminder
                                            try:
                                                perfil = buscar_perfil_por_telefone(from_number)
                                                nome_paciente = perfil.get('nome', '') if perfil else ''
                                                print(f"🟡 [rem_handler] Enviando notificacao de CANCELAMENTO (via reminder) ao dono")
                                                send_reminder_to_owner(
                                                    patient_name=nome_paciente,
                                                    date=dt.strftime('%d/%m/%Y') if dt else '',
                                                    time=dt.strftime('%H:%M') if dt else '',
                                                    isCancel=True
                                                )
                                                print(f"✅ [rem_handler] Notificacao de cancelamento enviada com SUCESSO ao dono")
                                            except Exception as e:
                                                print(f"🔴 [rem_handler] Erro ao notificar dono sobre cancelamento: {e}")
                                                logger.exception('[rem_handler] Failed to notify owner about cancellation: %s', e)
                                        else:
                                            send_text(from_number, 'Não foi possível cancelar. Tente novamente.')
                                        # remove matching lembretes
                                        try:
                                            remover_lembretes_por_appointment(app_iso, from_number)
                                        except Exception:
                                            logger.exception('[rem_handler] failed removing lembretes for appointment')
                                        continue
                                except Exception:
                                    logger.exception('[webhook] error handling reminder interactive reply')
                                    # fall through to normal processing if handler fails
                    elif itype == 'list_reply':  # resposta por lista
                        texto = inter.get('list_reply', {}).get('id')  # id selecionado
                # plain text
                if texto is None:  # se não foi interativo, tenta texto simples
                    txt = msg.get('text', {})  # parte text do payload
                    texto = txt.get('body') if isinstance(txt, dict) else None  # conteúdo textual

                # sent_wait flag: enviaremos 'Aguarde...' apenas imediatamente antes
                # de operações que consultam a planilha (dias/horários).
                # Não enviar de forma genérica ao receber qualquer input.
                sent_wait = False  # controla se a mensagem de espera já foi enviada
                # Primeiro-contato / cadastro: se essa for a primeira vez (sessão vazia),
                # verificar se já existe cadastro no Sheets; se não, solicitar nome completo.
                try:
                    perfil_existente = buscar_perfil_por_telefone(from_number)
                except Exception:
                    perfil_existente = None

                if wf.sessoes.get(from_number) is None:
                    # Sessão nova: se já estiver cadastrado, armazenar primeiro nome na sessão;
                    # caso contrário, pedir o nome completo e aguardar resposta.
                    if perfil_existente:
                        primeiro_nome = (perfil_existente.get('nome') or '').split()[0] if perfil_existente.get('nome') else None
                        if primeiro_nome:
                            wf.sessoes[from_number + '_first_name'] = primeiro_nome
                        # Inicializa o estado na sessão e envia o menu com saudação
                        wf.sessoes[from_number] = wf.MENU_PRINCIPAL
                        try:
                            saud = f"Olá, {wf.sessoes.get(from_number + '_first_name', '')}!\n"
                            menu_text, menu_items = wf.exibir_menu_principal()
                            send_menu_buttons(from_number, saud + menu_text, menu_items)
                        except Exception:
                            logger.exception('[webhook] Falha ao enviar menu inicial para usuário cadastrado')
                        # Após enviar o menu inicial, não processar a mesma mensagem novamente
                        continue
                    else:
                        # Pergunta pelo nome completo e marca estado de espera de cadastro
                        try:
                            send_text(from_number, MSG.ASK_FULL_NAME)
                        except Exception:
                            logger.exception('[webhook] Falha ao enviar pedido de nome no primeiro contato')
                        wf.sessoes[from_number] = 'esperar_nome'
                        # não delegar ao fluxo ainda; próxima mensagem será o nome
                        continue

                # Se estamos aguardando o nome do usuário, salvar no Sheets e seguir
                if wf.sessoes.get(from_number) == 'esperar_nome':
                    nome_completo = (texto or '').strip()
                    if nome_completo:
                        try:
                            perfil = criar_cadastro_paciente(from_number, nome_completo, origem='whatsapp_cloud')
                            primeiro_nome = (perfil.get('nome') or '').split()[0] if perfil.get('nome') else None
                            if primeiro_nome:
                                wf.sessoes[from_number + '_first_name'] = primeiro_nome
                        except Exception:
                            logger.exception('[webhook] Falha ao criar cadastro de paciente')
                            send_text(from_number, 'Desculpe, não consegui salvar seu cadastro. Tente novamente mais tarde.')
                            wf.sessoes.pop(from_number, None)
                            continue
                    # colocar estado no menu principal e mostrar menu
                    wf.sessoes[from_number] = wf.MENU_PRINCIPAL
                    try:
                        saud = f"Olá, {wf.sessoes.get(from_number + '_first_name', '')}!\n"
                        menu_text, menu_items = wf.exibir_menu_principal()
                        send_menu_buttons(from_number, saud + menu_text, menu_items)
                    except Exception:
                        logger.exception('[webhook] Falha ao enviar menu após cadastro')
                    continue
                try:
                    estado_atual = wf.sessoes.get(from_number)  # lê estado atual da sessão
                except Exception:
                    estado_atual = None  # se houver erro, fica None
                texto_lower = (str(texto or '')).strip().lower()  # versão minúscula do texto para heurísticas

                # call the flow
                try:
                    logger.info("[webhook] Estado antes de processar mensagem for %s: estado=%s texto=%s", from_number, estado_atual, texto)
                    resposta = wf.processar_mensagem(from_number, texto)  # delega processamento ao módulo de fluxo
                except Exception:
                    logger.exception("[webhook] Exception inside processar_mensagem")  # log de erro interno
                    resposta = "Desculpe, ocorreu um erro interno. Tente novamente mais tarde."  # fallback amigável

                logger.info("[webhook] Resposta do fluxo para %s: %s", from_number, resposta)  # log da resposta gerada

                # Decide how to reply: prefer interactive when menu-like
                # If the response contém as opções do menu principal, envia botões
                menu_text, menu_items = wf.exibir_menu_principal()

                # IMPORTANT: Detect if response contains BOTH confirmation message AND menu
                # If yes, send confirmation as text first, then menu buttons separately
                has_menu = menu_text in resposta or (MSG.MENU_PROMPT in resposta and MSG.LIST_BODY_TEXT in resposta)
                has_confirmation = '✅' in resposta and any(word in resposta for word in ['confirmado', 'realizado', 'cancelado'])

                if has_menu and has_confirmation:
                    # Split confirmation from menu: send confirmation first as text
                    try:
                        # Find where menu starts in the response
                        menu_start_idx = resposta.find(MSG.MENU_PROMPT)
                        if menu_start_idx > 0:
                            confirmation_part = resposta[:menu_start_idx].strip()
                            # Send confirmation message as text
                            send_text(from_number, confirmation_part)
                            # Then send menu buttons with greeting
                            saud = f"Olá, {wf.sessoes.get(from_number + '_first_name', '')}!\n" if wf.sessoes.get(from_number + '_first_name') else ''
                            send_menu_buttons(from_number, saud + menu_text, menu_items)
                        else:
                            # Fallback: just send as text if we can't split properly
                            send_text(from_number, resposta)
                    except Exception:
                        logger.exception('[webhook] Failed to split confirmation and menu; sending as text')
                        send_text(from_number, resposta)
                # Verifica se a resposta contém o texto do menu (permite texto adicional antes)
                elif menu_text in resposta or (MSG.MENU_PROMPT in resposta and MSG.LIST_BODY_TEXT in resposta):
                    # Ao reenviar o menu principal, envie primeiro qualquer texto que
                    # venha antes do menu (ex: mensagem de confirmação/aviso), depois
                    # envie os botões com a saudação + menu.
                    saud = f"Olá, {wf.sessoes.get(from_number + '_first_name', '')}!\n" if wf.sessoes.get(from_number + '_first_name') else ''
                    # procurar início do menu na resposta (prefere o menu_text)
                    menu_start_idx = resposta.find(menu_text)
                    if menu_start_idx == -1:
                        menu_start_idx = resposta.find(MSG.MENU_PROMPT)
                    # se houver texto antes do menu, enviá-lo como texto simples
                    if menu_start_idx > 0:
                        prefix = resposta[:menu_start_idx].strip()
                        try:
                            if prefix:
                                send_text(from_number, prefix)
                        except Exception:
                            logger.exception('[webhook] Failed to send prefix before menu')
                    # finalmente, enviar os botões com a saudação + menu
                    send_menu_buttons(from_number, saud + menu_text, menu_items)
                # Some flow branches prepend extra text (e.g. "Escolha a nova data e horário:\n" + exibir_semanas...)
                # so match more flexibly: if the response mentions 'escolha' and 'semana' or explicit 'nova data'
                elif ('semana' in resposta.lower() and 'escolh' in resposta.lower()) or ('escolha a nova data' in resposta.lower()) or ('escolha a data' in resposta.lower() and 'horário' in resposta.lower()):
                    # Ao mostrar semanas, apenas exibe o prompt de semanas (não adicionar texto extra)
                    send_weeks_buttons(from_number, MSG.WEEKS_PROMPT)  # envia botões de semana
                # Flexible match: if the response asks to choose a day (various phrasings), send interactive list
                elif (('dia' in resposta.lower() and 'escolh' in resposta.lower()) or resposta.lower().startswith('escolha o dia')):  # escolher dia
                    try:
                        if not sent_wait:  # envia mensagem de espera somente agora
                            send_text(from_number, MSG.WAIT_MSG)  # mensagem de aguarde
                            sent_wait = True  # marca como enviada
                    except Exception:
                        logger.exception('[webhook] Falha ao enviar mensagem de aguarde antes de obter dias')  # log se falhar ao enviar aguarde
                    offset = wf.sessoes.get(from_number + '_semana_offset', 0)  # offset da semana salvo na sessão
                    dias = wf.obter_dias_disponiveis_semana(offset)  # obtém dias disponíveis do fluxo
                    # IMPORTANTE: WhatsApp permite no máximo 10 rows por lista interativa
                    # Reservamos 2 slots para Voltar e Cancelar, então limitamos a 8 dias
                    if len(dias) > 8:
                        logger.warning('[webhook] Lista de dias truncada de %d para 8 (limite WhatsApp)', len(dias))
                        dias = dias[:8]
                    items = []  # prepara lista de rows
                    for i, d in enumerate(dias):  # formata cada dia
                        dia_pt = d.strftime('%d/%m/%Y')  # data formatada
                        semana_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d.weekday()]  # sempre usar abreviação para consistência
                        title = f"{semana_abrev}, {dia_pt}"  # formato: "Seg, 23/12/2025" (sempre cabe em 24 chars)
                        # Usar descrição vazia para evitar duplicação visual
                        items.append((f"{i+1}", title, ""))  # adiciona item sem descrição
                    # acrescenta Voltar/Cancelar como opções de lista (descrição vazia para evitar duplicação)
                    items.append(("0", MSG.LABEL_VOLTA, ""))
                    items.append(("9", MSG.LABEL_CANCEL, ""))
                    send_list_days(from_number, 'Escolha o dia', items)  # envia lista de dias
                # If the flow requests a confirmation, prefer confirm buttons (precise match before other list branches)
                elif 'confirma' in resposta.lower() or resposta.lower().startswith('confirmação'):
                    send_confirm_buttons(from_number, resposta)  # envia botões de confirmação para o usuário
                elif ('agendamento' in resposta.lower() and 'reagend' in resposta.lower()) or resposta.lower().startswith('escolha o agendamento para reagendar'):  # listar agendamentos para reagendar
                    ags = wf.sessoes.get('_lista_agendamentos') or []  # obtém lista salva na sessão
                    items = []  # prepara items
                    for i, (dt, linha) in enumerate(ags):  # formata cada agendamento
                        paciente = (linha[3] or 'Paciente')
                        # Sempre usar abreviação para consistência (Seg, Ter, etc)
                        title = f"{_abbr_weekday(dt.weekday())}, {dt.strftime('%d/%m')}"
                        desc = f"{dt.strftime('%H:%M')} - {paciente}"
                        items.append((f"{i+1}", title, desc))  # adiciona item com descrição
                    items.append(("0", MSG.LABEL_VOLTA, ""))  # Voltar
                    items.append(("9", MSG.LABEL_CANCEL, ""))  # Cancelar
                    send_list_days(from_number, 'Escolha o agendamento', items)  # envia lista de agendamentos
                elif resposta.lower().startswith('escolha o agendamento para cancelar'):
                    ags = wf.sessoes.get('_lista_agendamentos_cancelar') or []  # lista de agendamentos específicos para cancelamento
                    items = []  # prepara items
                    for i, (dt, linha) in enumerate(ags):  # formata cada agendamento
                        paciente = (linha[3] or 'Paciente')
                        # Sempre usar abreviação para consistência (Seg, Ter, etc)
                        title = f"{_abbr_weekday(dt.weekday())}, {dt.strftime('%d/%m')}"
                        desc = f"{dt.strftime('%H:%M')} - {paciente}"
                        items.append((f"{i+1}", title, desc))  # adiciona com descrição
                    items.append(("0", MSG.LABEL_VOLTA, ""))  # Voltar
                    items.append(("9", MSG.LABEL_CANCEL_APPOINTMENT, ""))  # Cancelar Agendamento (rótulo diferenciado)
                    send_list_days(from_number, 'Escolha o agendamento', items)  # envia lista para o usuário
                # if the flow asks for any confirmation (agendamento or cancelamento), send confirm buttons
                elif 'confirma' in resposta.lower() or resposta.lower().startswith('confirmação'):
                    send_confirm_buttons(from_number, resposta)  # envia botões de confirmação para o usuário
                # Flexible match for choosing a time/hours
                elif (('horar' in resposta.lower() or 'horário' in resposta.lower() or 'horario' in resposta.lower()) and 'escolh' in resposta.lower()) or resposta.lower().startswith('escolha o horário'):  # escolher horário
                    try:
                        if not sent_wait:  # envia mensagem de espera antes de consultar horários
                            send_text(from_number, MSG.WAIT_MSG)  # mensagem de aguarde
                            sent_wait = True  # marca flag
                    except Exception:
                        logger.exception('[webhook] Falha ao enviar mensagem de aguarde antes de obter horários')  # log erro
                    dia = wf.sessoes.get(from_number + '_dia_escolhido')  # dia previamente escolhido na sessão
                    horarios = wf.obter_horarios_disponiveis_para_dia(dia)  # consulta horários disponíveis no fluxo
                    items = []  # prepara items para lista
                    for i, h in enumerate(horarios):  # formata cada horário
                        items.append((f"{i+1}", h.strftime('%H:%M'), ''))  # adiciona horário com descrição vazia
                    items.append(("0", "Voltar", ""))  # Voltar
                    items.append(("9", "Cancelar", ""))  # Cancelar
                    send_list_times(from_number, 'Escolha o horário', items)  # envia lista de horários
                else:
                    # Se a resposta for uma indicação de "nenhum dia/horário disponível",
                    # enviar botões interativos Voltar/Cancelar em vez de texto puro.
                    try:
                        # Se for mensagem de "nenhum dia/horário" ou informações de pagamento,
                        # enviar botões Voltar/Cancelar para manter navegação guiada.
                        is_no_days = (MSG.NO_DAYS_AVAILABLE in resposta) or resposta.startswith(MSG.NO_DAYS_AVAILABLE)
                        is_no_hours = (MSG.NO_HOURS_AVAILABLE in resposta) or resposta.startswith(MSG.NO_HOURS_AVAILABLE)
                        is_payment = (hasattr(MSG, 'PAYMENT_TITLE') and MSG.PAYMENT_TITLE in resposta) or (hasattr(MSG, 'PAYMENT_INFO') and MSG.PAYMENT_INFO in resposta)
                        if is_payment:
                            # Na tela de pagamento, só oferecemos Voltar (sem Cancelar)
                            send_back_only_button(from_number, resposta)
                        elif is_no_days or is_no_hours:
                            send_back_cancel_buttons(from_number, resposta)
                        else:
                            send_text(from_number, resposta)  # envia resposta genérica em texto quando não há interativo aplicável
                    except Exception:
                        logger.exception('[webhook] falha ao enviar resposta de disponibilidade; enviando texto fallback')
                        send_text(from_number, resposta)
    return {'status': 'received'}  # responde 200 OK ao remetente do webhook


# Iniciar servidor apenas quando executado diretamente (não em imports)
if __name__ == "__main__":
    import uvicorn
    logger.info("[main] Starting Uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
