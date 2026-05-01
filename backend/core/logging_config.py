"""
Help DMEs — Configuração de Logging
=====================================
Configura logging com saída dupla:
  - Console (stdout): nível INFO — para acompanhar em tempo real
  - Arquivo rotativo: nível DEBUG — para análise posterior pelo dev/Opus
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level=logging.INFO):
    """
    Configura logging para toda a aplicação.
    Saída dupla: console (stdout) + arquivo rotativo (logs/help_dmes.log).
    """
    # Diretório de logs na raiz do projeto
    project_root = Path(__file__).resolve().parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "help_dmes.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1: Console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Handler 2: Arquivo rotativo (5MB, 3 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configurar logger raiz
    root = logging.getLogger("help_dmes")
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    root.info(f"Logging inicializado. Arquivo de log: {log_file}")
    return root
