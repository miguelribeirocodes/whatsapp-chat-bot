# Testes Automatizados do Bot

Esta pasta contém o framework de testes automatizado para o fluxo conversacional do WhatsApp Bot.

## Estrutura

- **test_fluxo_conversacional.py** - Framework de testes (TDD)
  - `TestadorFluxoConversacional` - Simula mensagens do usuário
  - `GeradorTestesFluxo` - Gera sequências de teste
  - Geração automática de relatórios

- **relatorio_testes_\*.txt** - Relatórios legíveis
- **relatorio_testes_\*.json** - Relatórios estruturados (para análise)

## Como Executar

```bash
# Executar todos os testes
python test_fluxo_conversacional.py

# Os relatórios serão gerados automaticamente:
# - relatorio_testes_<timestamp>.txt
# - relatorio_testes_<timestamp>.json
```

## Cobertura de Testes

### 1. Fluxos Válidos (Happy Path)
- Menu → Agendar → Voltar → Menu
- Menu → Agendar → Semana → Dia → Horário → Confirmar
- Menu → Cancelar (sem agendamentos)

### 2. Inputs Inválidos (Robustez)
- Texto aleatório no menu
- Caracteres inválidos em campos numéricos
- Strings vazias
- Espaços extras em inputs
- Números fora do intervalo válido

### 3. Alternância de Fluxos
- Agendar → Voltar → Reagendar
- Cancelar → Voltar → Agendar

## Resultado Esperado

✅ **100% de sucesso esperado** - O bot não deve quebrar em nenhum cenário

## Adicionando Novos Testes

Para adicionar novos testes, estenda a classe `GeradorTestesFluxo`:

```python
@staticmethod
def testes_seu_novo_caso() -> List[Tuple[str, List[str]]]:
    """Seu novo caso de teste"""
    return [
        ("Descrição do teste", ["input1", "input2", "input3"]),
    ]
```

Depois, adicione ao `main()`:

```python
# Adicionar nova categoria de testes
print("[X/X] Executando seus testes...")
for nome_teste, sequencia in gerador.testes_seu_novo_caso():
    testador.executar_teste(nome_teste, sequencia)
```

## Importantes

- ✅ Os testes **NÃO enviam mensagens reais** para WhatsApp
- ✅ Apenas testam a **lógica do fluxo conversacional**
- ✅ Executam em **segundos**
- ✅ Geram **relatórios detalhados** para análise
