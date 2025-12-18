from fastapi import FastAPI, Request, HTTPException  # importa FastAPI e tipos Request/HTTPException
import os  # importa módulo para variáveis de ambiente
import requests  # importa requests para chamadas HTTP à Graph API
from dotenv import load_dotenv  # importa load_dotenv para carregar .env
import logging  # importa logging para logs
import json  # importa json para serializar payloads de debug

logging.basicConfig(level=logging.INFO)  # configura logging básico em nível INFO
logger = logging.getLogger(__name__)  # obtém logger do módulo
from agenda_service import buscar_perfil_por_telefone, criar_cadastro_paciente


# Helpers para nomes dos dias da semana em português (usados nos títulos/descrições)
def _abbr_weekday(idx: int) -> str:  # retorna abreviação do dia da semana em PT
    return ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][idx]  # valores abreviados

def _full_weekday(idx: int) -> str:  # retorna o nome completo do dia da semana em PT
    return ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado','Domingo'][idx]  # valores completos

load_dotenv()  # carrega variáveis de ambiente de um arquivo .env quando presente

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # token do WhatsApp Cloud
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")  # id do telefone/container
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")  # token de verificação para webhook
GRAPH_API_BASE = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"  # endpoint da Graph API

import whatsapp_flow as wf  # importa lógica do fluxo conversacional (módulo local)
import messages as MSG
import scheduler

app = FastAPI()  # instancia FastAPI


def send_text(to: str, text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers para autorização e content-type
    payload = {  # payload JSON para mensagem de texto
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    try:
        logger.info("[send_text] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))  # log do payload enviado
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # chama a Graph API
        logger.info("[send_text] Response status=%s body=%s", r.status_code, r.text)  # log da resposta
        return r  # retorna o response para o chamador
    except Exception as e:
        logger.exception("[send_text] Exception while sending message")  # log de exceção se falhar
        raise  # re-levanta exceção para tratamento externo


def send_reminder(to: str, text: str):
    """Wrapper to send reminder messages (reuses send_text). Kept as a single place to extend later."""
    try:
        logger.info("[send_reminder] Sending reminder to %s text=%s", to, text)
        return send_text(to, text)
    except Exception:
        logger.exception("[send_reminder] Failed to send reminder to %s", to)
        raise


def send_reminder_to_owner(patient_name: str, date: str, time: str):
    """Send notification to clinic owner if configured in messages.py"""
    owner = MSG.CLINIC_OWNER_PHONE
    if not owner:
        logger.info("[send_reminder_to_owner] No CLINIC_OWNER_PHONE configured; skipping owner notification")
        return None
    text = MSG.OWNER_REMINDER_TEMPLATE.format(patient=patient_name, date=date, time=time)
    try:
        return send_text(owner, text)
    except Exception:
        logger.exception("[send_reminder_to_owner] Failed to notify owner %s", owner)
        return None


# Schedule daily summary for owner at configured hour
try:
    _owner_summary_sent_dates = set()

    def _owner_daily_summary():
        try:
            from agenda_service import obter_todos_agenda_cached
            from datetime import datetime
            todos = obter_todos_agenda_cached()[1:]
            hoje_dt = datetime.now()
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
        from datetime import datetime
        now = datetime.now()
        if now.hour >= schedule_hour:
            hoje = now.strftime('%d/%m/%Y')
            if hoje not in _owner_summary_sent_dates:
                logger.info('[daily_summary] current time past schedule hour, sending today summary now')
                _owner_daily_summary()
    except Exception:
        logger.exception('[daily_summary] error when checking immediate send')
except Exception:
    logger.exception('[webhook] Failed to schedule daily owner summary')

# (startup pending reminders logic is executed after helper functions are defined)


def send_menu_buttons(to: str, text: str):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}  # headers para autenticação
    # botões em português
    payload = {  # payload interativo do tipo button (até 3 botões)
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
                "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "1", "title": MSG.MENU_AGENDAR}},
                    {"type": "reply", "reply": {"id": "2", "title": MSG.MENU_REAGENDAR}},
                    {"type": "reply", "reply": {"id": "3", "title": MSG.MENU_CANCELAR}}
                ]
            }
        }
    }
    try:
        logger.info("[send_menu_buttons] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))  # log do envio
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia para Graph API
        logger.info("[send_menu_buttons] Response status=%s body=%s", r.status_code, r.text)  # log da resposta
        return r  # retorna response
    except Exception:
        logger.exception("[send_menu_buttons] Exception while sending buttons")  # log de erro
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
                    {"type": "reply", "reply": {"id": "9", "title": MSG.LABEL_CANCEL}}
                ]
            }
        }
    }
    try:
        logger.info("[send_weeks_buttons] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))  # log
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        logger.info("[send_weeks_buttons] Response status=%s body=%s", r.status_code, r.text)  # log resposta
        return r
    except Exception:
        logger.exception("[send_weeks_buttons] Exception while sending week buttons")  # log exceção
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
        logger.info("[send_list_days] Response status=%s body=%s", r.status_code, r.text)  # log resposta
        return r  # retorna response
    except Exception:
        logger.exception("[send_list_days] Exception while sending list of days")  # log exceção
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
        logger.info("[send_confirm_buttons] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))  # log
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        logger.info("[send_confirm_buttons] Response status=%s body=%s", r.status_code, r.text)  # log resposta
        return r  # retorna response
    except Exception:
        logger.exception("[send_confirm_buttons] Exception while sending confirm buttons")  # log exceção
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
        logger.info("[send_reminder_confirm_buttons] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)
        logger.info("[send_reminder_confirm_buttons] Response status=%s body=%s", r.status_code, r.text)
        return r
    except Exception:
        logger.exception("[send_reminder_confirm_buttons] Exception while sending reminder confirm buttons")
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
        logger.info("[send_back_cancel_buttons] Sending to %s payload=%s", to, json.dumps(payload, ensure_ascii=False))  # log
        r = requests.post(GRAPH_API_BASE, headers=headers, json=payload, timeout=15)  # envia
        logger.info("[send_back_cancel_buttons] Response status=%s body=%s", r.status_code, r.text)  # log resposta
        return r  # retorna response
    except Exception:
        logger.exception("[send_back_cancel_buttons] Exception while sending back/cancel buttons")  # log exceção
        raise  # re-levanta


# On startup, load pending reminders from sheet and schedule/send them
try:
    from agenda_service import obter_lembretes_pendentes, marcar_lembrete_como_enviado
    from datetime import datetime
    pendentes = obter_lembretes_pendentes()  # all pending
    for lemb in pendentes:
        sched = lemb['scheduled_dt']
        row = lemb['row']
        telefone = lemb['telefone']
        paciente = lemb['paciente']
        ag_dt = datetime.fromisoformat(lemb['appointment_iso']) if lemb.get('appointment_iso') else None
        if sched <= datetime.now():
            # send immediately (interactive confirm) and mark
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
                send_reminder_confirm_buttons(telefone, text, lemb['appointment_iso'])
            except Exception:
                logger.exception('[startup] failed to send pending reminder row=%s', row)
            try:
                marcar_lembrete_como_enviado(row)
            except Exception:
                logger.exception('[startup] failed to mark reminder sent row=%s', row)
        else:
            # schedule for future
            try:
                from scheduler import schedule_at
                def _send_and_mark_start(row=row, phone=telefone, date_text=lemb['appointment_date'], time_text=lemb['appointment_time'], appt_iso=lemb.get('appointment_iso')):
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
                        send_reminder_confirm_buttons(phone, texto, appt_iso)
                    except Exception:
                        logger.exception('[startup] failed sending scheduled reminder row=%s', row)
                    try:
                        marcar_lembrete_como_enviado(row)
                    except Exception:
                        logger.exception('[startup] failed marking sent row=%s', row)
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
    if mode == 'subscribe' and token == VERIFY_TOKEN:  # valida token recebido
        return int(challenge)  # retorna challenge para concluir verificação
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
                                    from agenda_service import cancelar_agendamento_por_data_hora, obter_lembretes_pendentes, marcar_lembrete_como_enviado
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
                                        # mark any matching lembretes for this appointment as sent
                                        pend = obter_lembretes_pendentes()
                                        for p in pend:
                                            if p.get('appointment_iso') == app_iso and p.get('telefone') == from_number:
                                                try:
                                                    marcar_lembrete_como_enviado(p['row'])
                                                except Exception:
                                                    logger.exception('[rem_handler] failed marking lembrete sent')
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
                                                cancelled = cancelar_agendamento_por_data_hora(dt)
                                            except Exception:
                                                logger.exception('[rem_handler] fail cancel')
                                        if cancelled:
                                            send_text(from_number, MSG.REMINDER_CANCELLED_MSG)
                                        else:
                                            send_text(from_number, 'Não foi possível cancelar. Tente novamente.')
                                        # mark matching lembretes as sent
                                        pend = obter_lembretes_pendentes()
                                        for p in pend:
                                            if p.get('appointment_iso') == app_iso and p.get('telefone') == from_number:
                                                try:
                                                    marcar_lembrete_como_enviado(p['row'])
                                                except Exception:
                                                    logger.exception('[rem_handler] failed marking lembrete sent')
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
                            send_menu_buttons(from_number, saud + wf.exibir_menu_principal())
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
                        send_menu_buttons(from_number, saud + wf.exibir_menu_principal())
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
                if ("Agendar" in resposta and "Reagendar" in resposta and "Cancelar" in resposta) or resposta == wf.exibir_menu_principal():
                    send_menu_buttons(from_number, resposta)  # envia botões do menu principal
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
                    items = []  # prepara lista de rows
                    for i, d in enumerate(dias):  # formata cada dia
                        dia_pt = d.strftime('%d/%m/%Y')  # data formatada
                        semana_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d.weekday()]  # abreviatura
                        semana_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'][d.weekday()]  # nome completo
                        title_full = f"{semana_pt}, {dia_pt}"  # título completo
                        # WhatsApp list row title max 24 chars — fallback para abreviação
                        if len(title_full) > 24:
                            title = f"{semana_abrev}, {dia_pt}"
                        else:
                            title = title_full
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
                        full_text = f"{_full_weekday(dt.weekday())}, {dt.strftime('%d/%m/%Y %H:%M')}"
                        # If full text fits in title limit, show full datetime as title and keep description minimal
                        if len(full_text) <= 24:
                            title = full_text
                            desc = paciente
                        else:
                            # Use short title (abbr weekday + date) and put time + patient in description
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
                        full_text = f"{_full_weekday(dt.weekday())}, {dt.strftime('%d/%m/%Y %H:%M')}"
                        if len(full_text) <= 24:
                            title = full_text
                            desc = paciente
                        else:
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
                    send_text(from_number, resposta)  # envia resposta genérica em texto quando não há interativo aplicável
    return {'status': 'received'}  # responde 200 OK ao remetente do webhook
