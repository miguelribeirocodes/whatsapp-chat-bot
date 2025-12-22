"""
test_fluxo_conversacional.py

Framework de testes automatizado para o fluxo conversacional do bot.
Testa todos os caminhos possíveis (happy path, inputs inválidos, edge cases)
SEM enviar mensagens reais para WhatsApp.

Uso:
    python test_fluxo_conversacional.py

Saída:
    - relatorio_testes_<timestamp>.json (dados estruturados)
    - relatorio_testes_<timestamp>.txt (relatório legível)
"""

import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Any
import traceback
import random
import string

# Desabilitar logs do WhatsApp e outras bibliotecas durante testes
logging.basicConfig(level=logging.CRITICAL)

# Importar apenas a função de processar mensagem
from whatsapp_flow import processar_mensagem, sessoes as flow_sessoes


class TestadorFluxoConversacional:
    """
    Simula um usuário (ou múltiplos usuários) enviando mensagens para o bot.
    Valida as respostas sem enviar nada para WhatsApp.
    """

    def __init__(self):
        self.usuario_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
        self.testes_executados = []
        self.testes_passaram = 0
        self.testes_falharam = 0
        self.estado_atual = "menu_principal"
        self.historico_mensagens = []

    def simular_mensagem(self, texto_mensagem: str) -> Dict[str, Any]:
        """
        Simula um usuário enviando uma mensagem e captura a resposta.

        Returns:
            Dict com:
            - input: mensagem enviada
            - resposta: resposta do bot
            - estado_anterior: estado antes de processar
            - estado_atual: estado após processar
            - sucesso: True se não houve exceção
            - erro: mensagem de erro (se houver)
        """
        try:
            # Capturar estado anterior
            estado_anterior = flow_sessoes.get(self.usuario_id, "menu_principal")

            # Processar mensagem (sem enviar para WhatsApp)
            resposta = processar_mensagem(self.usuario_id, texto_mensagem)

            # Capturar novo estado
            estado_atual = flow_sessoes.get(self.usuario_id, "menu_principal")

            # Registrar no histórico
            self.historico_mensagens.append({
                "timestamp": datetime.now().isoformat(),
                "entrada": str(texto_mensagem),
                "saida": resposta[:100] + "..." if len(resposta) > 100 else resposta,
                "estado_anterior": estado_anterior,
                "estado_atual": estado_atual
            })

            return {
                "input": texto_mensagem,
                "resposta": resposta,
                "estado_anterior": estado_anterior,
                "estado_atual": estado_atual,
                "sucesso": True,
                "erro": None
            }

        except Exception as e:
            estado_atual = flow_sessoes.get(self.usuario_id, "menu_principal")
            erro_msg = f"{type(e).__name__}: {str(e)}"

            self.historico_mensagens.append({
                "timestamp": datetime.now().isoformat(),
                "entrada": str(texto_mensagem),
                "saida": f"ERRO - {erro_msg}",
                "estado_anterior": estado_anterior if 'estado_anterior' in locals() else "desconhecido",
                "estado_atual": estado_atual,
                "traceback": traceback.format_exc()
            })

            return {
                "input": texto_mensagem,
                "resposta": None,
                "estado_anterior": estado_anterior if 'estado_anterior' in locals() else "desconhecido",
                "estado_atual": estado_atual,
                "sucesso": False,
                "erro": erro_msg,
                "traceback": traceback.format_exc()
            }

    def executar_teste(self, nome_teste: str, sequencia_inputs: List[str],
                       validacao_fn=None) -> Dict[str, Any]:
        """
        Executa uma sequência de inputs e opcionalmente valida o resultado.

        Args:
            nome_teste: identificação do teste
            sequencia_inputs: lista de mensagens para enviar
            validacao_fn: função opcional que recebe (resultado, respostas) -> bool

        Returns:
            Dict com resultado do teste
        """
        resultado = {
            "nome": nome_teste,
            "timestamp": datetime.now().isoformat(),
            "sequencia": sequencia_inputs,
            "respostas": [],
            "passou": False,
            "erro": None,
            "detalhes": ""
        }

        try:
            # Limpar sessão do usuário para este teste
            flow_sessoes.pop(self.usuario_id, None)

            # Executar cada mensagem
            for msg in sequencia_inputs:
                resultado_msg = self.simular_mensagem(msg)
                resultado["respostas"].append(resultado_msg)

                # Se uma mensagem falhou, parar
                if not resultado_msg["sucesso"]:
                    resultado["erro"] = resultado_msg["erro"]
                    resultado["detalhes"] = f"Falhou na entrada '{msg}': {resultado_msg['erro']}"
                    self.testes_falharam += 1
                    self.testes_executados.append(resultado)
                    return resultado

            # Aplicar validação customizada se fornecida
            if validacao_fn:
                passou = validacao_fn(resultado["respostas"])
                resultado["passou"] = passou
            else:
                # Sem validação customizada = passou se nenhum erro
                resultado["passou"] = True
                resultado["detalhes"] = "Sequência executada sem erros"

            if resultado["passou"]:
                self.testes_passaram += 1
            else:
                self.testes_falharam += 1
                resultado["detalhes"] = "Validação customizada falhou"

        except Exception as e:
            resultado["passou"] = False
            resultado["erro"] = str(e)
            resultado["detalhes"] = traceback.format_exc()
            self.testes_falharam += 1

        self.testes_executados.append(resultado)
        return resultado

    def gerar_relatorio(self, salvar_arquivo=True) -> str:
        """
        Gera relatório em formato texto legível.
        """
        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE TESTES DO FLUXO CONVERSACIONAL")
        relatorio.append("=" * 80)
        relatorio.append(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        relatorio.append(f"Total de testes: {len(self.testes_executados)}")
        relatorio.append(f"[PASSOU] {self.testes_passaram}")
        relatorio.append(f"[FALHOU] {self.testes_falharam}")
        relatorio.append("")

        # Resumo
        relatorio.append("=" * 80)
        relatorio.append("RESUMO")
        relatorio.append("=" * 80)

        taxa_sucesso = (self.testes_passaram / len(self.testes_executados) * 100) if self.testes_executados else 0
        relatorio.append(f"Taxa de sucesso: {taxa_sucesso:.1f}%")
        relatorio.append("")

        # Detalhes de cada teste
        relatorio.append("=" * 80)
        relatorio.append("DETALHES DOS TESTES")
        relatorio.append("=" * 80)
        relatorio.append("")

        for idx, teste in enumerate(self.testes_executados, 1):
            status = "[PASSOU]" if teste["passou"] else "[FALHOU]"
            relatorio.append(f"[{idx}] {status} - {teste['nome']}")
            relatorio.append(f"    Sequencia: {' -> '.join(teste['sequencia'][:3])}")
            if len(teste['sequencia']) > 3:
                relatorio.append(f"               ... ({len(teste['sequencia'])} inputs no total)")

            if teste['erro']:
                relatorio.append(f"    [ERRO] {teste['erro']}")

            relatorio.append(f"    Detalhes: {teste['detalhes']}")
            relatorio.append("")

        # Testes que falharam
        testes_falhados = [t for t in self.testes_executados if not t['passou']]
        if testes_falhados:
            relatorio.append("=" * 80)
            relatorio.append("TESTES QUE FALHARAM (ANÁLISE DETALHADA)")
            relatorio.append("=" * 80)
            relatorio.append("")

            for teste in testes_falhados:
                relatorio.append(f"TESTE: {teste['nome']}")
                relatorio.append(f"Erro: {teste['erro']}")
                relatorio.append("Sequencia de inputs e respostas:")

                for i, (entrada, resposta) in enumerate(zip(teste['sequencia'], teste['respostas']), 1):
                    status = "[OK]" if resposta['sucesso'] else "[ERRO]"
                    relatorio.append(f"  {i}. {status} Entrada: '{entrada}'")
                    relatorio.append(f"     Estado anterior: {resposta['estado_anterior']}")
                    relatorio.append(f"     Estado atual: {resposta['estado_atual']}")
                    if resposta['sucesso']:
                        relatorio.append(f"     Resposta: {resposta['resposta'][:80]}...")
                    else:
                        relatorio.append(f"     [ERRO] {resposta['erro']}")

                relatorio.append("")

        texto_relatorio = "\n".join(relatorio)

        # Salvar em arquivo
        if salvar_arquivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Salvar TXT
            nome_arquivo_txt = f"relatorio_testes_{timestamp}.txt"
            with open(nome_arquivo_txt, "w", encoding="utf-8") as f:
                f.write(texto_relatorio)

            # Salvar JSON
            nome_arquivo_json = f"relatorio_testes_{timestamp}.json"
            with open(nome_arquivo_json, "w", encoding="utf-8") as f:
                json.dump({
                    "resumo": {
                        "total": len(self.testes_executados),
                        "passou": self.testes_passaram,
                        "falhou": self.testes_falharam,
                        "taxa_sucesso": taxa_sucesso
                    },
                    "testes": self.testes_executados
                }, f, indent=2, ensure_ascii=False)

            print(f"\n[OK] Relatorio salvo em: {nome_arquivo_txt}")
            print(f"[OK] Dados JSON salvos em: {nome_arquivo_json}")

        return texto_relatorio


class GeradorTestesFluxo:
    """
    Gera sequências de teste automaticamente.
    """

    @staticmethod
    def gerar_inputs_aleatorios(quantidade=5) -> List[str]:
        """Gera inputs aleatórios para testar robustez."""
        inputs = []
        inputs.extend([
            "abc", "xyz", "!!!",  # texto aleatório
            "99999", "-1", "0",   # números inválidos
            "", "   ",            # vazio/espaços
            "menu", "voltar", "sair",  # palavras que parecem comandos
            "".join(random.choices(string.ascii_letters, k=10)),  # string aleatória
        ])
        return inputs[:quantidade]

    @staticmethod
    def testes_fluxo_valido() -> List[Tuple[str, List[str]]]:
        """
        Retorna lista de testes do fluxo válido (happy path).
        """
        return [
            ("Menu principal -> Agendar -> Voltar -> Menu",
             ["1", "9"]),

            ("Menu principal -> Agendar -> Semana -> Dia -> Horário -> Confirmar",
             ["1", "1", "1", "1", "1"]),

            ("Menu -> Cancelar (sem agendamentos)",
             ["3"]),
        ]

    @staticmethod
    def testes_fluxo_invalido() -> List[Tuple[str, List[str]]]:
        """
        Retorna lista de testes com inputs inválidos.
        """
        return [
            ("Menu principal com input inválido",
             ["abc", "1"]),

            ("Agendar com input aleatório em semana",
             ["1", "xyz", "1"]),

            ("Agendar -> Semana -> input inválido dia",
             ["1", "1", "999", "1"]),

            ("Input vazio no menu",
             ["", "1"]),

            ("Saudação com espaços extras",
             ["  oi  ", "1"]),
        ]

    @staticmethod
    def testes_alternancia_fluxo() -> List[Tuple[str, List[str]]]:
        """
        Retorna testes de alternância entre fluxos.
        """
        return [
            ("Menu -> Agendar -> Voltar -> Menu -> Reagendar",
             ["1", "9", "2"]),

            ("Menu -> Cancelar -> Voltar -> Agendar",
             ["3", "9", "1"]),
        ]


def main():
    """Função principal - executa todos os testes."""

    print("\n" + "="*80)
    print("INICIANDO TESTES DO FLUXO CONVERSACIONAL")
    print("="*80 + "\n")

    testador = TestadorFluxoConversacional()
    gerador = GeradorTestesFluxo()

    # ========================================================================
    # 1. TESTES DO FLUXO VÁLIDO (Happy Path)
    # ========================================================================
    print("[1/3] Executando testes do fluxo válido...")
    for nome_teste, sequencia in gerador.testes_fluxo_valido():
        testador.executar_teste(nome_teste, sequencia)

    # ========================================================================
    # 2. TESTES COM INPUTS INVÁLIDOS (Robustez)
    # ========================================================================
    print("[2/3] Executando testes com inputs inválidos...")
    for nome_teste, sequencia in gerador.testes_fluxo_invalido():
        testador.executar_teste(nome_teste, sequencia)

    # ========================================================================
    # 3. TESTES DE ALTERNÂNCIA DE FLUXO
    # ========================================================================
    print("[3/3] Executando testes de alternância de fluxo...")
    for nome_teste, sequencia in gerador.testes_alternancia_fluxo():
        testador.executar_teste(nome_teste, sequencia)

    # ========================================================================
    # GERAR E EXIBIR RELATÓRIO
    # ========================================================================
    print("\n" + "="*80)
    print("GERANDO RELATORIO...")
    print("="*80 + "\n")

    relatorio = testador.gerar_relatorio(salvar_arquivo=True)
    # Imprimir relatório com encoding safe
    try:
        print(relatorio)
    except UnicodeEncodeError:
        # Fallback para terminal Windows que não suporta Unicode
        print("[RELATORIO GERADO] Veja os arquivos de relatorio para detalhes completos")

    print("\n" + "="*80)
    print("TESTES CONCLUÍDOS")
    print("="*80 + "\n")

    return 0 if testador.testes_falharam == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
