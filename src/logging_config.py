"""
Configuração centralizada de logging para o bot de WhatsApp.

Suporta:
- Níveis de log configuráveis via variável de ambiente LOG_LEVEL
- Output para console (stdout) e arquivo (com rotação automática)
- Formato customizado com timestamp, nível, módulo e mensagem
"""

import logging
import logging.handlers
import os
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Obter nível de log da variável de ambiente (padrão: INFO)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Validar nível de log
VALID_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if LOG_LEVEL not in VALID_LEVELS:
    LOG_LEVEL = 'INFO'


def setup_logging():
    """
    Configura o sistema de logging com handlers para console e arquivo.

    Configuração:
    - Console: todos os logs de todas as módulos
    - Arquivo: logs/app.log com rotação automática (10MB, 5 backups)
    - Formato: YYYY-MM-DD HH:MM:SS [LEVEL] module - message
    - Nível: configurável via LOG_LEVEL no .env
    """

    # Criar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    # Remover handlers existentes para evitar duplicação
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Formato customizado para os logs
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)-8s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler para console (stdout/stderr)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler para arquivo com rotação automática
    try:
        # Criar diretório logs se não existir
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # RotatingFileHandler: máximo 10MB por arquivo, manter 5 backups
        file_handler = logging.handlers.RotatingFileHandler(
            filename='logs/app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Manter app.log.1, app.log.2, ..., app.log.5
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    except Exception as e:
        root_logger.warning(f"Não foi possível configurar logging em arquivo: {e}")

    # Log inicial
    root_logger.info(f"Sistema de logging inicializado - Nível: {LOG_LEVEL}")


# Configurar logging automaticamente ao importar este módulo
if __name__ != "__main__":
    setup_logging()
