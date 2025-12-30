"""
main.py - Ponto de entrada para rodar o bot no Google Cloud
Inicia o servidor FastAPI com Uvicorn
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Iniciar o servidor FastAPI."""
    # Configurações
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))

    # Executar uvicorn
    subprocess.run([
        sys.executable,
        '-m',
        'uvicorn',
        'src.whatsapp_webhook:app',
        f'--host={host}',
        f'--port={port}',
        '--no-access-log'
    ])

if __name__ == '__main__':
    main()
