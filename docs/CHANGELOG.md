# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

## [Não Publicado]

## [Versão Estável] - 2025-12-22

### Adicionado

- **Automatização ngrok** - Integração de pyngrok para criar túnel automático ao iniciar serviço em desenvolvimento
- **Framework de testes** - Suite de testes automatizados que simula fluxos sem enviar mensagens WhatsApp
  - Cobertura de happy path, inputs inválidos e alternância entre fluxos
  - Geração automática de relatórios (JSON e TXT)
- **Reorganização de código** - Estrutura em pastas (`src/`, `docs/`, `tests/`)
- **Documentação melhorada** - README.md, guias separados em pasta docs/

### Melhorado

- Estrutura de projeto mais clara e profissional
- Testes padronizados para cada patch novo
- Documentação centralizada

### Corrigido

- Encoding de saída em testes no Windows
- Organização de arquivos de documentação

---

## [Versão 1.0] - 2025-12-18 a 2025-12-22

### Refatoração Completa (18/12/2025)

#### Estrutura e Organização
- Criados arquivos `constants.py` e `flow_helpers.py` para eliminar hardcoding
- Refatoração em 6 etapas completadas:
  - **Etapa 1**: Estado MENU_PRINCIPAL (números mágicos → constantes nomeadas)
  - **Etapa 2**: Estados REAGENDAR e CANCELAR (eliminadas ~80 linhas de duplicação)
  - **Etapas 3-4**: Estados AGENDAR, ESCOLHER_DIA, ESCOLHER_HORARIO, CONFIRMAR

#### Melhorias de UX
- Renomeado botão "Cancelar" → "Cancelar Agendamento" (evita confusão)
- Removida opção "Sair" do menu principal
- Fallback melhorado para entradas desconhecidas
- Mensagens de confirmação com emojis e formatação visual

#### Funcionalidades Novas
- **Sistema de janela deslizante** - Slots gerados automaticamente para os próximos 30 dias
- **Inicialização automática de slots** - No startup do webhook
- **Scheduler diário** - Adiciona slots automaticamente à meia-noite (00:01)
- **Notificações ao dono melhoradas** - Um único template para reagendamentos com dados antigos e novos

#### Bugs Corrigidos
- Saudação duplicada para usuários cadastrados
- Menu não exibia botões após cancelamento
- Normalização de respostas interativas (ids numéricos)
- Lembretes relacionados marcados como enviados ao cancelar
- Proteção de cabeçalhos da aba Agenda

### Configuração como Serviço (22/12/2025)

- Adicionado `if __name__ == "__main__"` para permitir execução como serviço Windows
- Guia NSSM simplificado e validado
- Suporte completo para deployments em produção

---

## Próximos Passos

- [ ] Comprar domínio próprio para produção
- [ ] Implementar multi-bot com Opção 1 (múltiplos endpoints)
- [ ] CI/CD automatizado
- [ ] Autenticação de usuários
- [ ] Painel administrativo

---

## Convenções

Este projeto segue as diretrizes de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

### Categorias de Mudanças

- **Adicionado** - Novas funcionalidades
- **Melhorado** - Melhorias em funcionalidades existentes
- **Corrigido** - Bugs corrigidos
- **Removido** - Funcionalidades removidas
- **Depreciado** - Funcionalidades que serão removidas
- **Segurança** - Correções de segurança

### Workflow de Testes

A partir de 22/12/2025, todo patch novo DEVE:

1. Rodar suite de testes: `python tests/test_fluxo_conversacional.py`
2. Gerar relatório de testes
3. Incluir resultado dos testes no commit
4. 100% de testes passando é obrigatório para merge
