from datetime import datetime, timedelta, time, date, timezone  # importa tipos de data e hora da biblioteca padrão
import gspread                                         # importa gspread para integração com Google Sheets
from google.oauth2.service_account import Credentials  # importa credenciais do service account do Google
import logging                                         # importa logging para registros de eventos
import re

logger = logging.getLogger(__name__)                   # obtém logger do módulo

# Timezone do Brasil (GMT-3) - importante para servidor em UTC
BRAZIL_TZ_OFFSET = timedelta(hours=-3)

def agora_brasil() -> datetime:
    """Retorna o horário atual no fuso horário do Brasil (GMT-3)."""
    utc_now = datetime.now(timezone.utc)
    brazil_now = utc_now + BRAZIL_TZ_OFFSET
    return brazil_now.replace(tzinfo=None)  # naive datetime para comparar com dados da planilha

# -------------------------------------------------------
# Configuração da agenda em Google Sheets
# (mesmos valores do whatsapp_flow_simulado.py por enquanto)
# -------------------------------------------------------

GOOGLE_SERVICE_ACCOUNT_FILE = "service_account.json"   # nome do arquivo JSON de credenciais do service account
GOOGLE_SCOPES = [                                      # lista de escopos necessários para acessar as planilhas
    "https://www.googleapis.com/auth/spreadsheets"     # escopo com permissão de leitura e edição em planilhas
]
SPREADSHEET_ID = "1KATQvSyKPrCxAPdDDZk70IbfaKk2a1fxSx9Rk0R1h-Y"  # ID da planilha que armazena agenda e cadastros
NOME_ABA_AGENDA = "Agenda"                             # nome da aba onde ficam os slots da agenda
NOME_ABA_CADASTROS = "Cadastros"                       # nome da aba onde ficam os cadastros de pacientes

# -------------------------------------------------------
# Parâmetros da agenda / horários (fácil de ajustar)
# -------------------------------------------------------

HORA_INICIO_MANHA = time(hour=8, minute=0)             # início da janela da manhã (08:00)
HORA_FIM_MANHA = time(hour=12, minute=0)               # fim da janela da manhã (12:00)
HORA_INICIO_TARDE = time(hour=14, minute=0)            # início da janela da tarde (14:00)
HORA_FIM_TARDE = time(hour=17, minute=0)               # fim da janela da tarde (17:00)

DURACAO_CONSULTA_MIN = 50                              # duração da consulta em minutos
INTERVALO_DESCANSO_MIN = 10                            # intervalo entre consultas em minutos
PASSO_SLOT_MIN = DURACAO_CONSULTA_MIN + INTERVALO_DESCANSO_MIN  # passo entre inícios de slots (consulta + intervalo)

DIAS_UTEIS = {0, 1, 2, 3, 4}                           # dias úteis: 0=segunda, 1=terça, ..., 4=sexta
NUM_DIAS_GERAR_SLOTS = 30                              # número de dias a partir de hoje para gerar slots (valor padrão)

# Lista de nomes de dias em português, índice 0=segunda, ..., 6=domingo
NOMES_DIAS_PT = [                                      # lista para mapear weekday() -> nome em português
    "segunda-feira",                                   # índice 0
    "terça-feira",                                     # índice 1
    "quarta-feira",                                    # índice 2
    "quinta-feira",                                    # índice 3
    "sexta-feira",                                     # índice 4
    "sábado",                                          # índice 5
    "domingo",                                         # índice 6
]

# -------------------------------------------------------
# Variáveis globais de cache (para gspread)
# -------------------------------------------------------

_gspread_client = None                                 # cache do cliente gspread autenticado
_worksheet_agenda = None                               # cache da worksheet (aba Agenda)
_cache = {}


# -------------------------------------------------------
# Funções auxiliares de acesso ao Google Sheets
# -------------------------------------------------------

def obter_cliente_gspread():
    """
    Retorna um cliente gspread autenticado com o service account.
    Usa cache em variável global para evitar reautenticação contínua.
    """
    global _gspread_client                              # indica que vamos usar a variável global de cliente

    if _gspread_client is not None:                     # se já existe um cliente em cache
        return _gspread_client                          # retorna o cliente existente

    creds = Credentials.from_service_account_file(      # cria credenciais a partir do JSON do service account
        GOOGLE_SERVICE_ACCOUNT_FILE,                    # caminho do arquivo de credenciais
        scopes=GOOGLE_SCOPES                            # escopos necessários para acesso às planilhas
    )

    _gspread_client = gspread.authorize(creds)          # autoriza e cria o cliente gspread
    return _gspread_client                              # retorna o cliente criado


def _obter_planilha():
    """
    Retorna o objeto da planilha principal de agenda/cadastros.
    Separado para reutilização interna.
    """
    cliente = obter_cliente_gspread()                   # obtém o cliente gspread autenticado
    planilha = cliente.open_by_key(SPREADSHEET_ID)      # abre a planilha pelo ID
    return planilha                                     # retorna a planilha aberta


def obter_worksheet_agenda():
    """
    Retorna a worksheet (aba) 'Agenda'.
    Se não existir, cria com a estrutura:
      dia_semana | data | hora | nome_paciente | telefone | status | origem | observacoes
    Garante que o cabeçalho esteja correto.
    """
    global _worksheet_agenda                            # usa variável global de cache de worksheet

    if _worksheet_agenda is not None:                   # se já existe em cache
        return _worksheet_agenda                        # retorna diretamente a worksheet

    planilha = _obter_planilha()                        # obtém a planilha principal

    try:
        ws = planilha.worksheet(NOME_ABA_AGENDA)        # tenta obter a aba "Agenda"
    except gspread.WorksheetNotFound:                   # se a aba não existir
        ws = planilha.add_worksheet(                    # cria uma nova aba
            title=NOME_ABA_AGENDA,                      # nome da aba
            rows=500,                                   # número inicial de linhas
            cols=8                                      # número de colunas esperadas
        )
        ws.update(                                      # escreve o cabeçalho na primeira linha
            "A1:H1",                                    # intervalo de cabeçalho
            [[                                          # lista com uma única linha
                "dia_semana",                           # coluna A
                "data",                                 # coluna B (dd/mm/aaaa)
                "hora",                                 # coluna C (HH:MM)
                "nome_paciente",                        # coluna D
                "telefone",                             # coluna E
                "status",                               # coluna F (DISPONIVEL, AGENDADO, etc.)
                "origem",                               # coluna G (whatsapp, manual, etc.)
                "observacoes"                           # coluna H
            ]]
        )

    primeira_linha = ws.row_values(1)                   # lê o conteúdo da primeira linha
    expected_headers = [
        "dia_semana",
        "data",
        "hora",
        "nome_paciente",
        "telefone",
        "status",
        "origem",
        "observacoes",
    ]

    try:
        normalized_first = [c.strip().lower() for c in primeira_linha[: len(expected_headers)]]
    except Exception:
        normalized_first = []

    # Se a primeira linha não corresponder aos cabeçalhos esperados,
    # presumimos que a linha de cabeçalho foi deletada ou corrompida.
    # Nesse caso, inserimos a linha de cabeçalho acima do primeiro item.
    if normalized_first != expected_headers:
        try:
            ws.insert_row(expected_headers, index=1)
        except Exception:
            # fallback: tentar sobrescrever A1:H1 (caso insert_row não esteja disponível)
            try:
                ws.update("A1:H1", [expected_headers])
            except Exception:
                # se falhar, prosseguimos sem interromper; operações posteriores podem falhar
                pass

    _worksheet_agenda = ws                              # armazena em cache a worksheet
    return ws                                           # retorna a worksheet pronta


def obter_todos_agenda_cached(ttl_seconds: int = 5):
    """Retorna todas as linhas da aba Agenda usando cache em memória por alguns segundos.
    Isso ajuda a reduzir leituras repetidas e evitar estourar o quota do Google Sheets.
    """
    key = 'agenda_all_values'
    import time
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry[0] < ttl_seconds:
        return entry[1]
    ws = obter_worksheet_agenda()
    try:
        vals = ws.get_all_values()
    except Exception:
        # se falhar e houver cache anterior, retorna fallback
        if entry:
            return entry[1]
        raise
    _cache[key] = (now, vals)
    return vals

def obter_worksheet_cadastros():
    """
    Retorna a worksheet (aba) 'Cadastros'.
    Se não existir, cria com a estrutura:
      telefone | nome | data_cadastro | origem | observacoes
    Garante que o cabeçalho esteja correto.
    """
    planilha = _obter_planilha()                        # abre a planilha principal

    try:
        ws = planilha.worksheet(NOME_ABA_CADASTROS)     # tenta obter a aba "Cadastros"
    except gspread.WorksheetNotFound:                   # se a aba não for encontrada
        ws = planilha.add_worksheet(                    # cria uma nova aba
            title=NOME_ABA_CADASTROS,                   # define o nome da aba
            rows=100,                                   # número inicial de linhas
            cols=5                                      # quantidade de colunas
        )
        ws.update(                                      # grava o cabeçalho na primeira linha
            "A1:E1",
            [[
                "telefone",                             # coluna A
                "nome",                                 # coluna B
                "data_cadastro",                        # coluna C
                "origem",                               # coluna D
                "observacoes"                           # coluna E
            ]]
        )

    primeira_linha = ws.row_values(1)                   # lê a primeira linha da aba
    if not primeira_linha:                              # se estiver vazia
        ws.update(                                      # reescreve o cabeçalho
            "A1:E1",
            [[
                "telefone",
                "nome",
                "data_cadastro",
                "origem",
                "observacoes"
            ]]
        )

    return ws                                           # retorna a worksheet de cadastros


# -------------------------------------------------------
# Funções de CADASTROS (perfis de pacientes)
# -------------------------------------------------------

def buscar_perfil_por_telefone(telefone: str):
    """
    Procura na aba 'Cadastros' um registro com o telefone informado.
    Se encontrar, retorna {"telefone": ..., "nome": ...}.
    Se não encontrar, retorna None.
    """
    ws = obter_worksheet_cadastros()                    # obtém a worksheet 'Cadastros'
    registros = ws.get_all_records()                    # lê todos os registros como dicionários

    telefone_str = str(telefone).strip()                # normaliza o telefone como string sem espaços

    for reg in registros:                               # percorre cada registro da planilha
        tel_reg = str(reg.get("telefone", "")).strip()  # obtém o telefone da linha atual
        if tel_reg == telefone_str:                     # compara com o telefone procurado
            nome_reg = reg.get("nome", "").strip() or "Paciente sem nome"  # pega o nome ou usa padrão
            logger.debug(f"Perfil encontrado para telefone {telefone_str}: {nome_reg}")  # loga o resultado
            return {"telefone": telefone_str, "nome": nome_reg}  # retorna dicionário de perfil

    logger.debug(f"Nenhum cadastro encontrado para telefone {telefone_str}.")  # loga ausência de cadastro
    return None                                          # indica que não achou nenhum registro


def criar_cadastro_paciente(telefone: str, nome: str, origem: str = "whatsapp_cloud"):
    """
    Cria um novo cadastro na aba 'Cadastros' com telefone e nome informados.
    Não verifica duplicidade; essa verificação deve ser feita antes.
    Retorna um dicionário de perfil compatível com o restante do código.
    """
    ws = obter_worksheet_cadastros()                    # obtém a worksheet 'Cadastros'

    telefone_str = str(telefone).strip()                # normaliza telefone em string
    nome_final = (nome or "").strip() or "Paciente sem nome"  # normaliza nome e aplica padrão
    data_cadastro = agora_brasil().strftime("%d/%m/%Y %H:%M")  # formata data/hora de cadastro (Brasil GMT-3)

    nova_linha = [                                      # monta a nova linha para a planilha
        telefone_str,                                   # coluna A: telefone
        nome_final,                                     # coluna B: nome
        data_cadastro,                                  # coluna C: data_cadastro
        origem,                                         # coluna D: origem do cadastro
        "Cadastro criado automaticamente pelo bot de WhatsApp."  # coluna E: observações
    ]

    ws.append_row(                                      # adiciona a linha na aba 'Cadastros'
        nova_linha,                                     # dados a serem gravados
        value_input_option="USER_ENTERED"               # deixa o Sheets interpretar os valores
    )

    logger.debug(                                       # loga a criação do novo cadastro
        f"Novo cadastro criado: telefone={telefone_str}, nome={nome_final}, origem={origem}"
    )
    return {"telefone": telefone_str, "nome": nome_final}  # retorna o dicionário de perfil criado


# -------------------------------------------------------
# Funções auxiliares de geração de horários (slots)
# -------------------------------------------------------

def gerar_slots_para_dia(data_dia: date):
    """
    Gera todos os horários (slots) possíveis para um dia específico,
    respeitando:
      - dias úteis (DIAS_UTEIS)
      - janelas de horário (manhã / tarde)
      - duração da consulta + intervalo
    Retorna uma lista de datetime (início de cada slot).
    """
    if data_dia.weekday() not in DIAS_UTEIS:            # se não for dia útil
        return []                                       # retorna lista vazia

    slots = []                                          # lista de slots
    passo = timedelta(minutes=PASSO_SLOT_MIN)           # passo entre inícios dos slots

    inicio_manha = datetime.combine(data_dia, HORA_INICIO_MANHA)  # início da manhã
    fim_manha = datetime.combine(data_dia, HORA_FIM_MANHA)        # fim da manhã

    atual = inicio_manha                               # horário atual da manhã
    while True:                                        # laço para gerar slots da manhã
        termino = atual + timedelta(minutes=DURACAO_CONSULTA_MIN)  # término da consulta
        if termino > fim_manha:                        # se ultrapassar o fim da manhã
            break                                      # interrompe laço
        slots.append(atual)                            # adiciona slot
        atual = atual + passo                          # avança para o próximo início

    inicio_tarde = datetime.combine(data_dia, HORA_INICIO_TARDE)  # início da tarde
    fim_tarde = datetime.combine(data_dia, HORA_FIM_TARDE)        # fim da tarde

    atual = inicio_tarde                               # horário atual da tarde
    while True:                                        # laço para gerar slots da tarde
        termino = atual + timedelta(minutes=DURACAO_CONSULTA_MIN)  # término da consulta
        if termino > fim_tarde:                        # se ultrapassar o fim da tarde
            break                                      # interrompe laço
        slots.append(atual)                            # adiciona slot
        atual = atual + passo                          # avança para o próximo

    return slots                                       # retorna lista de slots gerados


def obter_nome_dia_semana(data_dia: date) -> str:
    """
    Retorna o nome do dia da semana em português para uma data específica.
    """
    weekday = data_dia.weekday()                       # obtém índice do dia da semana (0–6)
    return NOMES_DIAS_PT[weekday]                      # retorna o nome correspondente


def obter_intervalo_semana_atual_a_partir_de_hoje():
    """
    Retorna (data_inicio, data_fim) da semana atual a partir de hoje.

    Regras:
      - Se hoje é segunda a sexta: início = hoje, fim = sexta desta semana.
      - Se hoje é sábado/domingo: início = próxima segunda, fim = próxima sexta.
    """
    hoje = date.today()                                # data de hoje
    weekday = hoje.weekday()                           # índice do dia da semana

    if weekday <= 4:                                   # se for segunda a sexta
        inicio = hoje                                  # início é hoje
        dias_ate_sexta = 4 - weekday                   # quantos dias até sexta
        fim = hoje + timedelta(days=dias_ate_sexta)    # fim é sexta desta semana
    else:                                              # se for sábado ou domingo
        dias_ate_proxima_segunda = 7 - weekday         # dias até próxima segunda
        inicio = hoje + timedelta(days=dias_ate_proxima_segunda)  # próxima segunda
        fim = inicio + timedelta(days=4)               # sexta da próxima semana

    return inicio, fim                                 # retorna tupla (início, fim)

def obter_intervalo_semana_relativa(offset_semanas: int = 0):
    """
    Calcula o intervalo de uma semana relativa à semana atual.
    offset_semanas:
      0  -> semana atual
      1  -> semana que vem
     -1  -> semana passada
      2  -> daqui 2 semanas, etc.
    """
    # Primeiro pegamos o intervalo “padrão” da semana atual.                    # usa lógica existente
    inicio_atual, fim_atual = obter_intervalo_semana_atual_a_partir_de_hoje()   # datas da semana atual

    # Se o deslocamento for zero, simplesmente devolvemos o intervalo atual.    # caso mais simples
    if offset_semanas == 0:                                                    # nenhuma semana de deslocamento
        return inicio_atual, fim_atual                                         # retorna semana atual

    # Cada semana adiciona (ou subtrai) 7 dias no intervalo.                    # define o delta em dias
    delta_dias = 7 * offset_semanas                                            # converte semanas em dias

    # Aplica o deslocamento para a data inicial e final.                        # desloca o intervalo inteiro
    novo_inicio = inicio_atual + timedelta(days=delta_dias)                    # início da semana relativa
    novo_fim = fim_atual + timedelta(days=delta_dias)                          # fim da semana relativa

    # Retorna o novo par (início, fim) já deslocado.                            # devolve o resultado
    hoje = date.today()                                # data de hoje
    weekday = hoje.weekday()                           # índice do dia da semana
    return novo_inicio - timedelta(days=weekday), novo_fim                                               # tuple de (date, date)

def extrair_intervalo_semana_da_mensagem(texto: str):
    """
    Tenta identificar, no texto do usuário, pedidos de semana relativa como:
      - "esta semana"
      - "essa semana"
      - "semana que vem" / "próxima semana"
      - "semana passada"
      - "daqui 2 semanas"
    Retorna (data_inicio, data_fim) ou None se não reconhecer nenhum padrão.
    """
    # Garante que estamos trabalhando com string e normaliza para minúsculas.   # normalização do texto
    texto_lower = (texto or "").lower()                                        # evita None e padroniza

    # --- Caso 1: expressões do tipo "daqui X semanas" ------------------------
    padrao_daqui = r"daqui\s+(\d+)\s+semanas?"                                 # regex para capturar o número X
    m = re.search(padrao_daqui, texto_lower)                                   # tenta encontrar o padrão no texto

    if m:                                                                      # se encontrou "daqui X semanas"
        qtd = int(m.group(1))                                                  # converte o X capturado para inteiro
        return obter_intervalo_semana_relativa(qtd)                            # devolve a semana relativa futura
    
    if "daqui a uma semana" in texto_lower or "daqui a 1 semana" in texto_lower:  # caso especial para 1 semana
        return obter_intervalo_semana_relativa(1)                              # retorna intervalo da próxima semana
    
    if "daqui a duas semanas" in texto_lower or "daqui a 2 semanas" in texto_lower:  # caso especial para 2 semanas
        return obter_intervalo_semana_relativa(2)                              # retorna intervalo de duas semanas à frente
    
    if "daqui a três semanas" in texto_lower or "daqui a 3 semanas" in texto_lower:  # caso especial para 3 semanas 
        return obter_intervalo_semana_relativa(3)                              # retorna intervalo de três semanas à frente

    # --- Caso 2: "semana que vem" / "próxima semana" -------------------------
    if "semana que vem" in texto_lower or "próxima semana" in texto_lower or "proxima semana" in texto_lower or "semana q vem" in texto_lower:
        # offset = 1 -> próxima semana                                         # desloca uma semana
        return obter_intervalo_semana_relativa(1)                              # retorna intervalo da semana que vem

    # --- Caso 3: "esta semana" / "essa semana" / "semana atual" --------------
    if "esta semana" in texto_lower or "essa semana" in texto_lower or "semana atual" in texto_lower:
        # offset = 0 -> semana atual                                           # sem deslocamento
        return obter_intervalo_semana_relativa(0)                              # retorna intervalo da semana atual

    # # --- Caso 4: "semana passada" / "última semana" --------------------------
    # if "semana passada" in texto_lower or "última semana" in texto_lower or "ultima semana" in texto_lower:
    #     # offset = -1 -> semana anterior                                       # desloca uma semana para trás
    #     return obter_intervalo_semana_relativa(-1)                             # retorna intervalo da semana passada

    # Futuramente você pode expandir aqui para casos como:                     # deixa espaço para evoluções
    #  - "primeira semana do mês que vem"                                      # exemplos de próximas features
    #  - "última semana deste mês"                                             # etc.
    # bastando interpretar o mês/ano e devolver (data_inicio, data_fim).       # sempre retornando o intervalo

    # Se nada foi reconhecido, retorna None.                                   # padrão: não encontrou expressão de semana
    return None                                                                # sinaliza ausência de intervalo semanal

def gerar_slots_semana_atual_a_partir_de_agora():
    """
    Gera slots teóricos para a semana atual (definida por obter_intervalo_semana_atual_a_partir_de_hoje),
    considerando apenas horários que ainda não passaram em relação ao momento atual.
    """
    agora = agora_brasil()                             # obtém data/hora atual (Brasil GMT-3)
    inicio_semana, fim_semana = obter_intervalo_semana_atual_a_partir_de_hoje()  # intervalo da semana

    slots_totais = []                                  # lista geral de slots
    dia_atual = inicio_semana                          # começa no dia de início

    while dia_atual <= fim_semana:                     # percorre até o fim da semana
        slots_dia = gerar_slots_para_dia(dia_atual)    # gera slots para o dia
        for slot in slots_dia:                         # percorre cada slot
            if slot >= agora:                          # se slot ainda não passou
                slots_totais.append(slot)              # adiciona à lista
        dia_atual = dia_atual + timedelta(days=1)      # avança um dia

    return slots_totais                                # retorna lista de slots


def obter_primeiro_slot_disponivel():
    """
    Retorna o primeiro horário teórico disponível da semana atual a partir de agora,
    baseado apenas na geração teórica de slots (não cruza com planilha).
    """
    slots = gerar_slots_semana_atual_a_partir_de_agora()  # gera slots
    if not slots:                                        # se lista vazia
        return None                                      # retorna None
    return slots[0]                                      # retorna primeiro slot


# -------------------------------------------------------
# Funções que cruzam slots TEÓRICOS com a planilha Agenda
# -------------------------------------------------------

def carregar_mapa_slots_existentes(ws):
    """
    Lê todas as linhas da aba Agenda e monta um set com pares (data, hora),
    para sabermos rapidamente quais slots já existem.

    Retorna:
        conjunto {(data_str, hora_str), ...}
    """
    registros = ws.get_all_records()                    # obtém registros da aba Agenda
    existentes = set()                                  # cria set vazio para armazenar tuplas
    for reg in registros:                               # percorre cada registro
        data_str = reg.get("data", "").strip()          # lê campo data
        hora_str = reg.get("hora", "").strip()          # lê campo hora
        if data_str and hora_str:                       # se ambos não estiverem vazios
            existentes.add((data_str, hora_str))        # adiciona par (data, hora) ao set
    return existentes                                   # retorna o conjunto de slots existentes


def inicializar_slots_proximos_dias(num_dias: int = NUM_DIAS_GERAR_SLOTS):
    """
    Gera linhas na aba Agenda para todos os slots possíveis
    dos próximos `num_dias` dias (começando hoje), respeitando:

      - dias úteis (segunda a sexta)
      - janelas de horário (manhã/tarde)
      - duração da consulta + intervalo
      - NÃO cria linhas duplicadas se (data, hora) já existir.

    Para cada novo slot criado, grava:
      dia_semana, data, hora, "", "", "DISPONIVEL", "", ""
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda

    existentes = carregar_mapa_slots_existentes(ws)     # carrega mapa de (data, hora) já existentes

    hoje = date.today()                                 # obtém a data de hoje

    novas_linhas = []                                   # lista para acumular linhas a serem inseridas

    for i in range(num_dias):                           # itera de 0 até num_dias-1
        dia = hoje + timedelta(days=i)                  # calcula a data correspondente

        if dia.weekday() not in DIAS_UTEIS:             # se não for dia útil
            continue                                    # pula para o próximo dia

        slots = gerar_slots_para_dia(dia)               # gera slots teóricos para esse dia

        for slot in slots:                              # percorre cada datetime de slot
            data_str = slot.strftime("%d/%m/%Y")        # formata data como dd/mm/aaaa
            hora_str = slot.strftime("%H:%M")           # formata hora como HH:MM

            if (data_str, hora_str) in existentes:      # se par já existe na planilha
                continue                                # não cria novamente

            weekday = dia.weekday()                     # índice do dia da semana
            nome_dia = NOMES_DIAS_PT[weekday]           # nome do dia em português

            nova_linha = [                              # monta linha para esse slot
                nome_dia,
                data_str,
                hora_str,
                "",
                "",
                "DISPONIVEL",
                "",
                ""
            ]
            novas_linhas.append(nova_linha)             # adiciona à lista de novas linhas

    if novas_linhas:                                    # se há linhas novas para inserir
        primeira_linha_vazia = len(ws.get_all_values()) + 1  # calcula primeira linha livre
        ultimo_indice = primeira_linha_vazia + len(novas_linhas) - 1  # calcula última linha a preencher
        intervalo = f"A{primeira_linha_vazia}:H{ultimo_indice}"       # monta intervalo A:H correto

        ws.update(                                      # atualiza planilha em bloco
            intervalo,
            novas_linhas
        )
        logger.debug(f"Foram criados {len(novas_linhas)} novos slots na Agenda.")  # log de debug
    else:
        logger.debug("Nenhum novo slot precisou ser criado (todos já existiam).")  # log indicando ausência de novos slots


def adicionar_slots_dia_futuro():
    """
    Adiciona slots para o dia que está exatamente NUM_DIAS_GERAR_SLOTS dias no futuro.

    Exemplo: Se NUM_DIAS_GERAR_SLOTS = 30 e hoje é 18/12/2025,
    esta função adiciona slots para 17/01/2026 (daqui 30 dias).

    Chamada diariamente pelo scheduler para manter uma janela deslizante.
    RESPEITA slots com status "FOLGA" (inseridos manualmente pelo dono).
    """
    import logging
    logger = logging.getLogger(__name__)

    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda

    # Carrega todos os slots existentes COM seus status
    todos_valores = ws.get_all_values()
    slots_existentes_com_status = {}  # {(data_str, hora_str): status}

    for linha in todos_valores[1:]:  # Ignora cabeçalho
        if len(linha) >= 6:
            data_str = linha[1].strip()
            hora_str = linha[2].strip()
            status = linha[5].strip().upper()
            if data_str and hora_str:
                slots_existentes_com_status[(data_str, hora_str)] = status

    hoje = date.today()                                 # obtém a data de hoje
    dia_futuro = hoje + timedelta(days=NUM_DIAS_GERAR_SLOTS)  # calcula dia futuro

    # Se não for dia útil, não há nada a fazer
    if dia_futuro.weekday() not in DIAS_UTEIS:
        logger.info('[daily_slots] Dia %s não é dia útil, pulando', dia_futuro.strftime('%d/%m/%Y'))
        return

    slots = gerar_slots_para_dia(dia_futuro)            # gera slots teóricos para esse dia
    novas_linhas = []                                   # lista para acumular linhas novas

    for slot in slots:                                  # percorre cada datetime de slot
        data_str = slot.strftime("%d/%m/%Y")            # formata data como dd/mm/aaaa
        hora_str = slot.strftime("%H:%M")               # formata hora como HH:MM

        # Verifica se slot já existe
        if (data_str, hora_str) in slots_existentes_com_status:
            status_existente = slots_existentes_com_status[(data_str, hora_str)]
            # Se o status for FOLGA, NÃO mexer (foi inserido manualmente)
            if status_existente == "FOLGA":
                logger.info('[daily_slots] Slot %s %s tem status FOLGA, mantendo', data_str, hora_str)
                continue
            # Se já existir com qualquer outro status, não criar duplicado
            continue

        weekday = dia_futuro.weekday()                  # índice do dia da semana
        nome_dia = NOMES_DIAS_PT[weekday]               # nome do dia em português

        nova_linha = [                                  # monta linha para esse slot
            nome_dia,
            data_str,
            hora_str,
            "",
            "",
            "DISPONIVEL",
            "",
            ""
        ]
        novas_linhas.append(nova_linha)                 # adiciona à lista de novas linhas

    if novas_linhas:                                    # se há linhas novas para inserir
        primeira_linha_vazia = len(ws.get_all_values()) + 1  # calcula primeira linha livre
        ultimo_indice = primeira_linha_vazia + len(novas_linhas) - 1  # calcula última linha a preencher
        intervalo = f"A{primeira_linha_vazia}:H{ultimo_indice}"       # monta intervalo A:H correto

        ws.update(                                      # atualiza planilha em bloco
            intervalo,
            novas_linhas
        )
        logger.info('[daily_slots] Criados %d novos slots para %s', len(novas_linhas), data_str)
    else:
        logger.info('[daily_slots] Nenhum novo slot criado para %s (já existiam ou eram folgas)',
                   dia_futuro.strftime('%d/%m/%Y'))


def obter_slots_disponiveis_para_data(data_dia: date):
    """
    Lê a aba Agenda e retorna uma lista de datetime para os slots que:
      - têm 'data' == data_dia
      - têm status == 'DISPONIVEL'
      - ainda não passaram em relação ao horário atual
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda
    try:
        registros = ws.get_all_records()                # lê registros como dicionários
    except Exception:
        # Fallback quando o cabeçalho da planilha estiver inconsistente
        # (gspread lança GSpreadException sobre cabeçalhos duplicados).
        vals = ws.get_all_values()
        if not vals or len(vals) < 2:
            registros = []
        else:
            # Cabeçalhos esperados em A..H
            headers = ['dia_semana', 'data', 'hora', 'nome_paciente', 'telefone', 'status', 'origem', 'observacoes']
            registros = []
            for row in vals[1:]:
                rowdict = {headers[i]: (row[i] if i < len(row) else '') for i in range(len(headers))}
                registros.append(rowdict)
    agora = agora_brasil()                              # obtém data/hora atual (Brasil GMT-3)
    data_str_alvo = data_dia.strftime("%d/%m/%Y")       # formata data alvo como string

    slots = []                                          # lista para acumular slots encontrados

    for reg in registros:                               # percorre cada registro
        data_str = reg.get("data", "").strip()          # lê campo data
        hora_str = reg.get("hora", "").strip()          # lê campo hora
        status = reg.get("status", "").strip().upper()  # lê campo status em maiúsculas

        if not data_str or not hora_str:                # se faltar data ou hora
            continue                                    # ignora

        if data_str != data_str_alvo:                   # se data não for a data alvo
            continue                                    # ignora

        if status != "DISPONIVEL":                      # se não estiver disponível
            continue                                    # ignora

        try:                                            # tenta converter data+hora em datetime
            dt_slot = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
        except ValueError:                              # se não conseguir converter
            continue                                    # ignora

        if dt_slot >= agora:                            # considera apenas horários futuros
            slots.append(dt_slot)                       # adiciona slot à lista

    slots.sort()                                        # ordena slots cronologicamente
    return slots                                        # retorna lista de slots disponíveis

def obter_slots_disponiveis_no_intervalo(data_inicio: date, data_fim: date):
    """
    Retorna TODOS os slots disponíveis (status = 'DISPONIVEL') entre
    data_inicio e data_fim (inclusive), percorrendo dia a dia.
    """
    # Se o usuário passar as datas invertidas (início > fim), fazemos um swap.   # garante que data_inicio <= data_fim
    if data_inicio > data_fim:                                                 # compara as duas datas
        data_inicio, data_fim = data_fim, data_inicio                          # troca as variáveis de lugar

    # Lista que vai acumular todos os datetimes de slots disponíveis.           # inicializa a lista de retorno
    slots_encontrados = []                                                     # começa com lista vazia

    # Começamos a varrer a partir de data_inicio.                               # define o cursor de varredura
    data_dia = data_inicio                                                     # primeiro dia do intervalo

    # Laço que percorre todos os dias até data_fim (inclusive).                # varre o intervalo dia a dia
    while data_dia <= data_fim:                                                # enquanto não ultrapassar a data final

        # Opcional: se você quiser filtrar só dias úteis, pode manter este if.  # aqui respeitamos o conceito de DIAS_UTEIS
        if data_dia.weekday() in DIAS_UTEIS:                                   # verifica se o dia é útil (seg a sex)
            # Usa a função já existente para buscar os slots desse dia.        # reaproveita lógica já pronto
            slots_do_dia = obter_slots_disponiveis_para_data(data_dia)         # lê os slots disponíveis na aba Agenda

            # Adiciona todos os slots desse dia na lista geral.                # acumula os datetimes encontrados
            slots_encontrados.extend(slots_do_dia)                              # junta na lista principal

        # Avança um dia no calendário.                                         # passa para o próximo dia
        data_dia = data_dia + timedelta(days=1)                                # soma 1 dia à data atual

    # Retorna a lista consolidada de slots.                                     # devolve o resultado
    return slots_encontrados                                                   # lista de datetimes disponíveis no intervalo

def obter_slots_disponiveis_semana_atual_a_partir_de_hoje():
    """
    Retorna todos os slots disponíveis na semana atual, a partir de hoje,
    reaproveitando a função genérica obter_slots_disponiveis_no_intervalo().
    """
    # Usa a função já existente para descobrir o intervalo da semana atual.     # obtém data de início e fim da semana
    inicio_semana, fim_semana = obter_intervalo_semana_atual_a_partir_de_hoje()  # retorna duas datas (date)

    # Apenas delega para a função genérica de intervalo.                        # reutiliza a lógica central
    return obter_slots_disponiveis_no_intervalo(                                # retorna lista de datetimes disponíveis
        data_inicio=inicio_semana,                                              # data inicial da semana
        data_fim=fim_semana                                                     # data final da semana
    )

def extrair_slots_semana(data_inicio, data_fim):
    # Wrapper genérico que devolve todos os slots disponíveis entre duas datas, # explica o objetivo
    # delegando a leitura efetiva para o módulo agenda_service.                 # menciona que não acessa planilha direto
    return obter_slots_disponiveis_no_intervalo(                         # chama a função genérica de intervalo
        data_inicio=data_inicio,                                                # passa a data inicial
        data_fim=data_fim                                                       # passa a data final
    )

def registrar_agendamento_google_sheets(
    nome_paciente,
    data_hora_consulta,
    origem="whatsapp_simulado",
    telefone="",
    observacoes=""
):
    """
    Marca um agendamento para um slot específico na aba Agenda.

    Lógica:
      - Procura uma linha na Agenda com (data, hora) correspondentes.
      - Se encontrar:
          -> se status != "DISPONIVEL", retorna False (não sobrescreve).
          -> se status == "DISPONIVEL", atualiza dados e retorna True.
      - Se NÃO encontrar:
          -> cria uma nova linha completa para esse slot já com status="AGENDADO"
             e retorna True.
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda

    data_str = data_hora_consulta.strftime("%d/%m/%Y")  # formata data como dd/mm/aaaa
    hora_str = data_hora_consulta.strftime("%H:%M")     # formata hora como HH:MM
    weekday = data_hora_consulta.date().weekday()       # obtém índice do dia da semana
    nome_dia = NOMES_DIAS_PT[weekday]                   # obtém nome do dia em português

    todos_valores = ws.get_all_values()                 # lê toda a planilha como matriz
    linha_encontrada = None                             # variável para guardar índice da linha encontrada
    linha_conteudo = None                               # variável para guardar conteúdo da linha

    for idx, linha in enumerate(todos_valores[1:], start=2):  # percorre linhas (ignorando cabeçalho)
        if len(linha) < 3:                              # se não tiver colunas suficientes
            continue                                    # ignora
        data_exist = linha[1].strip()                   # coluna B = data
        hora_exist = linha[2].strip()                   # coluna C = hora
        if data_exist == data_str and hora_exist == hora_str:  # se data e hora coincidirem
            linha_encontrada = idx                      # guarda índice da linha
            linha_conteudo = linha                      # guarda conteúdo da linha
            break                                       # interrompe laço

    if linha_encontrada is not None:                    # se encontrou linha existente
        status_existente = ""                           # inicializa status
        if linha_conteudo and len(linha_conteudo) >= 6:  # se linha tem coluna de status
            status_existente = linha_conteudo[5].strip().upper()  # lê status em maiúsculas

        if status_existente and status_existente != "DISPONIVEL":  # se já não estiver disponível
            return False                                 # não sobrescreve, retorna False

        intervalo = f"A{linha_encontrada}:H{linha_encontrada}"  # monta intervalo da linha
        nova_linha = [                                  # monta linha atualizada
            nome_dia,
            data_str,
            hora_str,
            nome_paciente,
            telefone,
            "AGENDADO",
            origem,
            observacoes,
        ]
        ws.update(intervalo, [nova_linha])              # grava na planilha
        return True                                     # retorna sucesso

    # Se não encontrou slot existente, cria nova linha com esse horário já como AGENDADO.
    nova_linha = [
        nome_dia,
        data_str,
        hora_str,
        nome_paciente,
        telefone,
        "AGENDADO",
        origem,
        observacoes,
    ]
    ws.append_row(
        nova_linha,
        value_input_option="USER_ENTERED"
    )
    return True                                         # retorna sucesso


def cancelar_agendamento_por_data_hora(dt_consulta: datetime, telefone_esperado: str = None) -> bool:
    """
    Procura na aba Agenda uma linha com a data/hora informadas.
    Se encontrar e o slot estiver AGENDADO:
      - limpa nome_paciente, telefone, origem, observacoes
      - coloca status = 'DISPONIVEL'
      - retorna True

    Se não encontrar ou não estiver AGENDADO, retorna False.

    IMPORTANTE: Se telefone_esperado for fornecido, valida se o telefone do agendamento
    bate com o esperado (segurança: evita que um usuário cancele agendamento de outro).
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda
    todos_valores = ws.get_all_values()                 # lê todas as linhas

    if not todos_valores or len(todos_valores) < 2:     # se estiver vazia ou só com cabeçalho
        return False                                    # nada a cancelar

    data_str = dt_consulta.strftime("%d/%m/%Y")         # formata data
    hora_str = dt_consulta.strftime("%H:%M")            # formata hora

    linha_encontrada = None                             # índice da linha encontrada
    linha_conteudo = None                               # conteúdo da linha encontrada

    for idx, linha in enumerate(todos_valores[1:], start=2):  # percorre a partir da linha 2
        if len(linha) < 6:                              # se não tiver colunas suficientes
            continue                                    # ignora

        data_exist = linha[1].strip()                   # lê data existente
        hora_exist = linha[2].strip()                   # lê hora existente
        status_exist = linha[5].strip().upper()         # lê status existente

        if data_exist == data_str and hora_exist == hora_str:  # se bater data e hora
            linha_encontrada = idx                      # guarda índice da linha
            linha_conteudo = linha                      # guarda conteúdo da linha
            break                                       # interrompe laço

    if linha_encontrada is None:                        # se não encontrou linha
        return False                                    # não há o que cancelar

    # SEGURANÇA: validar telefone se foi fornecido
    if telefone_esperado:
        telefone_agenda = (linha_conteudo[4].strip() if len(linha_conteudo) > 4 else "")
        if telefone_agenda != telefone_esperado:
            logger.warning("[cancelar_agendamento] Tentativa de cancelar agendamento de outro usuário: esperado=%s encontrado=%s", telefone_esperado, telefone_agenda)
            return False  # Nega cancelamento de agendamento de outro usuário

    status_exist = (linha_conteudo[5].strip().upper() if len(linha_conteudo) >= 6 else "")  # status atual
    if status_exist != "AGENDADO":                      # só cancela se estiver AGENDADO
        return False                                    # caso contrário, retorna False

    weekday = dt_consulta.date().weekday()              # obtém índice do dia da semana
    nome_dia = NOMES_DIAS_PT[weekday]                   # nome do dia

    nova_linha = [                                      # monta linha limpa
        nome_dia,
        data_str,
        hora_str,
        "",
        "",
        "DISPONIVEL",
        "",
        ""
    ]

    intervalo = f"A{linha_encontrada}:H{linha_encontrada}"  # intervalo da linha inteira
    ws.update(intervalo, [nova_linha])               # atualiza na planilha

    # Além de limpar o slot na aba Agenda, marcar lembretes relacionados
    # como enviados para evitar que sejam reenviados no restart.
    try:
        appt_iso = dt_consulta.isoformat()
        telefone_exist = (linha_conteudo[4].strip() if len(linha_conteudo) > 4 else None)
        # remove any pending reminders for this appointment and telefone
        try:
            remover = remover_lembretes_por_appointment
            remover(appt_iso, telefone_exist)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('[cancel] failed removing lembretes for appointment=%s tel=%s', appt_iso, telefone_exist)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('[cancel] error while removing lembretes after cancellation')

    return True                                         # retorna sucesso


def buscar_proximo_agendamento_por_telefone(telefone: str):
    """
    Busca o PRÓXIMO agendamento futuro associado a um telefone específico,
    sem alterá-lo na planilha.

    Retorna:
      - datetime do agendamento encontrado, se houver
      - None se não encontrar nenhum agendamento futuro para esse telefone.
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda
    todos_valores = ws.get_all_values()                 # lê todas as linhas

    if not todos_valores or len(todos_valores) < 2:     # se não há dados
        return None                                     # retorna None

    agora = agora_brasil()                              # obtém data/hora atual (Brasil GMT-3)
    melhor_dt = None                                    # melhor datetime encontrado

    for linha in todos_valores[1:]:                     # percorre a partir da linha 2
        if len(linha) < 6:                              # verifica se há colunas suficientes
            continue                                    # ignora

        telefone_exist = linha[4].strip()               # coluna E = telefone
        status_exist = linha[5].strip().upper()         # coluna F = status

        if telefone_exist != telefone:                  # se telefone não bater
            continue                                    # ignora

        if status_exist != "AGENDADO":                  # se status não for AGENDADO
            continue                                    # ignora

        data_str = linha[1].strip()                     # coluna B = data
        hora_str = linha[2].strip()                     # coluna C = hora

        try:
            dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")  # monta datetime
        except ValueError:
            continue                                    # ignora se não conseguir converter

        if dt < agora:                                  # se já passou
            continue                                    # ignora

        if melhor_dt is None or dt < melhor_dt:         # se for o mais próximo
            melhor_dt = dt                              # atualiza melhor_dt

    return melhor_dt                                    # retorna melhor_dt (ou None)


# -------------------------------------------------------
# Funções de persistência de lembretes
# -------------------------------------------------------
NOME_ABA_LEMBRETES = "Lembretes"


def obter_worksheet_lembretes():
    planilha = _obter_planilha()
    try:
        ws = planilha.worksheet(NOME_ABA_LEMBRETES)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=NOME_ABA_LEMBRETES, rows=1000, cols=10)
        ws.update("A1:J1", [[
            "scheduled_iso", "appointment_iso", "appointment_date", "appointment_time",
            "telefone", "paciente", "tipo", "sent_at", "created_at", "observacoes"
        ]])
    primeira = ws.row_values(1)
    if not primeira:
        ws.update("A1:J1", [[
            "scheduled_iso", "appointment_iso", "appointment_date", "appointment_time",
            "telefone", "paciente", "tipo", "sent_at", "created_at", "observacoes"
        ]])
    return ws


def registrar_lembrete_agendamento(appointment_dt, scheduled_dt, telefone, paciente, tipo="patient_reminder", observacoes=""):
    """Registra um lembrete na aba Lembretes. Retorna o índice da linha criada (1-based)."""
    ws = obter_worksheet_lembretes()
    scheduled_iso = scheduled_dt.isoformat()
    appointment_iso = appointment_dt.isoformat()
    appointment_date = appointment_dt.strftime("%d/%m/%Y")
    appointment_time = appointment_dt.strftime("%H:%M")
    created_at = agora_brasil().isoformat()  # timestamp Brasil GMT-3
    row = [scheduled_iso, appointment_iso, appointment_date, appointment_time, str(telefone), paciente, tipo, "", created_at, observacoes]
    ws.append_row(row, value_input_option="USER_ENTERED")
    all_values = ws.get_all_values()
    return len(all_values)  # row index of appended row


def obter_lembretes_pendentes(ate_dt=None):
    """Retorna lista de lembretes pendentes (sent_at vazio). Se ate_dt fornecido, filtra scheduled_iso <= ate_dt."""
    ws = obter_worksheet_lembretes()
    rows = ws.get_all_values()
    resultados = []
    now = agora_brasil()  # Usa horário do Brasil
    for idx, linha in enumerate(rows[1:], start=2):
        # A: scheduled_iso, H: sent_at
        if len(linha) < 8:
            continue
        scheduled_iso = linha[0].strip()
        sent_at = linha[7].strip()
        if sent_at:
            continue
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_iso)
        except Exception:
            # ignore malformed
            continue
        if ate_dt and scheduled_dt > ate_dt:
            continue
        resultados.append({
            "row": idx,
            "scheduled_dt": scheduled_dt,
            "appointment_iso": linha[1].strip(),
            "appointment_date": linha[2].strip(),
            "appointment_time": linha[3].strip(),
            "telefone": linha[4].strip(),
            "paciente": linha[5].strip(),
            "tipo": linha[6].strip(),
            "observacoes": linha[9].strip() if len(linha) > 9 else ""
        })
    return resultados


def marcar_lembrete_como_enviado(row_index):
    """Marca o lembrete na linha especificada com timestamp de envio."""
    ws = obter_worksheet_lembretes()
    sent_iso = agora_brasil().isoformat()  # timestamp Brasil GMT-3
    cell = f"H{row_index}"
    # gspread Worksheet.update expects a 2D list for ranges; use update_acell for single cell
    try:
        ws.update_acell(cell, sent_iso)
    except Exception:
        # fallback to update with proper 2D values
        try:
            ws.update(cell, [[sent_iso]])
        except Exception:
            # as a last resort, try to delete the row (best-effort)
            try:
                ws.delete_rows(row_index)
                return True
            except Exception:
                raise
    return True


def remover_lembrete_por_row(row_index):
    """Remove a linha do lembrete indicada pelo índice (1-based).
    Retorna True se removido, False caso contrário.
    """
    ws = obter_worksheet_lembretes()
    try:
        ws.delete_rows(row_index)
        return True
    except Exception:
        return False


def remover_lembretes_por_appointment(appointment_iso, telefone):
    """Remove todos os lembretes pendentes que correspondam a um appointment_iso + telefone.
    IMPORTANTE: `telefone` é obrigatório para evitar remover lembretes de outros usuários.

    A remoção sempre tentará casar por:
      - telefone (obrigatório)
      - data + horário do agendamento (formato planilha: `appointment_date` = dd/mm/YYYY, `appointment_time` = HH:MM)

    Retorna o número de linhas removidas.
    """
    ws = obter_worksheet_lembretes()
    pend = obter_lembretes_pendentes()
    rows_to_delete = []

    if not telefone:
        logger.warning("[remover_lembretes_por_appointment] REJEITADO: telefone obrigatório não fornecido")
        return 0

    # normalize target date/time from appointment_iso when possible
    target_date = None
    target_time = None
    from datetime import datetime
    if appointment_iso:
        try:
            dt = datetime.fromisoformat(appointment_iso)
            target_date = dt.strftime("%d/%m/%Y")
            target_time = dt.strftime("%H:%M")
        except Exception:
            target_date = None
            target_time = None

    for p in pend:
        # Ensure the record has expected fields
        appt_date = p.get('appointment_date')
        appt_time = p.get('appointment_time')
        tel = p.get('telefone')

        # SEGURANÇA: validar telefone SEMPRE
        if str(tel) != str(telefone):
            continue

        if target_date and target_time:
            match_dt = (appt_date == target_date and appt_time == target_time)
        else:
            # fallback to comparing appointment_iso strings
            match_dt = (p.get('appointment_iso') == appointment_iso)
        if not match_dt:
            continue

        rows_to_delete.append(p['row'])

    if not rows_to_delete:
        return 0
    # delete from bottom to top to avoid shifting indices
    rows_to_delete = sorted(set(rows_to_delete), reverse=True)
    removed = 0
    for r in rows_to_delete:
        try:
            ws.delete_rows(r)
            removed += 1
        except Exception:
            continue
    return removed


def cancelar_proximo_agendamento_por_telefone(telefone: str):
    """
    Cancela o PRÓXIMO agendamento futuro associado a um telefone específico.
    Regras:
      - procura na aba Agenda linhas com:
          * telefone igual ao informado
          * status == 'AGENDADO'
          * data/hora ainda futuras
      - escolhe o agendamento mais próximo do momento atual
      - limpa os dados do paciente e coloca status = 'DISPONIVEL'
      - retorna o datetime do agendamento cancelado
      - se não encontrar nada, retorna None
    """
    ws = obter_worksheet_agenda()                       # obtém worksheet da Agenda
    todos_valores = ws.get_all_values()                 # lê todas as linhas

    if not todos_valores or len(todos_valores) < 2:     # se não há dados
        return None                                     # nada a cancelar

    agora = agora_brasil()                              # data/hora atual (Brasil GMT-3)

    melhor_linha = None                                 # índice da linha com melhor agendamento
    melhor_dt = None                                    # datetime do melhor agendamento

    for idx, linha in enumerate(todos_valores[1:], start=2):  # percorre linhas de dados
        if len(linha) < 6:                              # se não tiver colunas suficientes
            continue                                    # ignora

        telefone_exist = linha[4].strip()               # telefone da linha
        status_exist = linha[5].strip().upper()         # status da linha

        if telefone_exist != telefone:                  # se telefone não bater
            continue                                    # ignora

        if status_exist != "AGENDADO":                  # se não estiver AGENDADO
            continue                                    # ignora

        data_str = linha[1].strip()                     # data da linha
        hora_str = linha[2].strip()                     # hora da linha

        try:
            dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")  # monta datetime
        except ValueError:
            continue                                    # ignora se não converter

        if dt < agora:                                  # se já passou
            continue                                    # ignora

        if melhor_dt is None or dt < melhor_dt:         # se for mais próximo
            melhor_dt = dt                              # atualiza melhor_dt
            melhor_linha = idx                          # guarda linha correspondente

    if melhor_linha is None:                            # se não achou nenhum agendamento
        return None                                     # retorna None

    weekday = melhor_dt.date().weekday()                # obtém índice do dia da semana
    nome_dia = NOMES_DIAS_PT[weekday]                   # obtém nome do dia

    nova_linha = [                                      # monta linha com slot livre
        nome_dia,
        melhor_dt.strftime("%d/%m/%Y"),
        melhor_dt.strftime("%H:%M"),
        "",
        "",
        "DISPONIVEL",
        "",
        ""
    ]

    intervalo = f"A{melhor_linha}:H{melhor_linha}"      # intervalo da linha
    ws.update(intervalo, [nova_linha])                  # atualiza na planilha

    # Além de limpar o slot na aba Agenda, marcar lembretes relacionados
    # como enviados para evitar que sejam reenviados no restart.
    try:
        appt_iso = melhor_dt.isoformat()
        try:
            remover = remover_lembretes_por_appointment
            remover(appt_iso, telefone)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('[cancel_prox] failed removing lembretes for appointment=%s', appt_iso)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('[cancel_prox] error while removing lembretes after cancellation')

    return melhor_dt                                    # retorna datetime do agendamento cancelado


# -------------------------------------------------------
# Funções de listagem / resumo de agendamentos
# -------------------------------------------------------

def listar_agendamentos_para_data(data_dia: date):
    """
    Retorna todos os agendamentos com status 'AGENDADO' para uma data específica.
    """
    ws = obter_worksheet_agenda()                       # obtém a worksheet 'Agenda'
    registros = ws.get_all_records()                    # lê todos os registros como dicionários

    data_str_alvo = data_dia.strftime("%d/%m/%Y")       # formata a data alvo como string
    agendamentos = []                                   # lista para armazenar os agendamentos do dia

    for reg in registros:                               # percorre cada registro da planilha
        data_reg = str(reg.get("data", "")).strip()     # obtém o campo de data
        status = str(reg.get("status", "")).strip().upper()  # obtém o status em maiúsculas

        if data_reg != data_str_alvo:                   # ignora registros de outras datas
            continue                                    # passa para o próximo registro
        if status != "AGENDADO":                        # ignora registros que não estão agendados
            continue                                    # passa para o próximo registro

        agendamentos.append(reg)                        # adiciona o registro à lista de agendados

    return agendamentos                                 # retorna a lista de agendamentos encontrados


def montar_texto_resumo_dia(data_dia: date):
    """
    Monta o texto da mensagem de resumo diário dos agendamentos.
    """
    agendamentos = listar_agendamentos_para_data(data_dia)  # obtém todos os agendamentos do dia
    data_str = data_dia.strftime("%d/%m/%Y")                # formata a data como texto

    if not agendamentos:                                    # verifica se não há agendamentos
        return f"Bom dia! Hoje ({data_str}) não há consultas agendadas."  # mensagem simples de agenda vazia

    agendamentos_ordenados = sorted(                        # cria nova lista ordenada
        agendamentos,                                       # usa a lista original
        key=lambda r: str(r.get("hora", ""))                # ordena pelo campo 'hora' em string
    )

    linhas = [                                              # lista de linhas de texto da mensagem
        f"Bom dia! Resumo das consultas de hoje ({data_str}):"  # cabeçalho da mensagem
    ]

    for reg in agendamentos_ordenados:                      # percorre cada agendamento ordenado
        hora = str(reg.get("hora", "")).strip()             # obtém horário da consulta
        nome = str(reg.get("nome_paciente", "")).strip() or "Paciente"  # obtém nome do paciente
        telefone = str(reg.get("telefone", "")).strip()     # obtém telefone do paciente
        linhas.append(                                      # adiciona uma linha formatada
            f"- {hora} – {nome} ({telefone})"
        )

    return "\n".join(linhas)                                # junta todas as linhas em um único texto
