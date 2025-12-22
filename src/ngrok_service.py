"""
Gerenciamento automático de túnel ngrok para desenvolvimento local.

Configuração via .env:
- NGROK_ENABLED=true/false (padrão: false)
- NGROK_AUTH_TOKEN=seu_token_aqui (obtém em https://dashboard.ngrok.com/)
- NGROK_REGION=us (região padrão)

Uso:
    import ngrok_service  # Auto-inicia se NGROK_ENABLED=true

    if ngrok_service.is_enabled():
        url = ngrok_service.get_tunnel_url()
        print(f"Webhook: {url}/webhook")
"""

import os
import logging
from pyngrok import ngrok
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
logger = logging.getLogger(__name__)

# Estado global
_tunnel = None
_public_url = None
_enabled = os.getenv('NGROK_ENABLED', 'false').lower() == 'true'


def is_enabled():
    """
    Retorna True se ngrok está habilitado via .env

    Returns:
        bool: True se NGROK_ENABLED=true, False caso contrário
    """
    return _enabled


def get_tunnel_url():
    """
    Retorna URL pública do túnel ngrok

    Returns:
        str: URL pública (ex: https://abc123.ngrok-free.app) ou None se desabilitado
    """
    return _public_url


def start():
    """
    Inicia túnel ngrok na porta 8000

    O túnel é criado com TLS habilitado e pode ser configurado com autenticação
    via NGROK_AUTH_TOKEN para obter URLs persistentes (plano pago).
    """
    global _tunnel, _public_url

    if not _enabled:
        logger.info("[ngrok] Disabled via environment variable")
        return

    if _tunnel is not None:
        logger.warning("[ngrok] Tunnel already running")
        return

    try:
        # Configurar autenticação se fornecida
        auth_token = os.getenv('NGROK_AUTH_TOKEN')
        if auth_token and auth_token.strip():
            ngrok.set_auth_token(auth_token)
            logger.info("[ngrok] Auth token configured")

        logger.info("[ngrok] Starting tunnel on port 8000...")

        # Criar túnel (sintaxe correta do pyngrok)
        # O ngrok.connect() retorna um Ngrok object com public_url
        _tunnel = ngrok.connect(8000, "http")
        _public_url = _tunnel.public_url

        # Log proeminente da URL para fácil localização nos logs
        logger.info("=" * 70)
        logger.info("[ngrok] Tunnel established!")
        logger.info("[ngrok] Public URL: %s", _public_url)
        logger.info("[ngrok] Webhook URL: %s/webhook", _public_url)
        logger.info("=" * 70)

    except Exception as e:
        logger.error("[ngrok] Failed to start tunnel: %s", e)
        logger.warning("[ngrok] Service will start without tunnel")
        _tunnel = None
        _public_url = None


def stop():
    """
    Para túnel ngrok de forma segura

    Desconecta o túnel e limpa as variáveis globais.
    """
    global _tunnel, _public_url

    if _tunnel is not None:
        try:
            ngrok.disconnect(_tunnel.public_url)
            logger.info("[ngrok] Tunnel disconnected")
        except Exception as e:
            logger.warning("[ngrok] Error disconnecting: %s", e)
        finally:
            _tunnel = None
            _public_url = None


# Auto-start ao importar módulo (se habilitado no .env)
if _enabled:
    start()
