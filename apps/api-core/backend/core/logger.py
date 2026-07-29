"""
Configuración de logging para la aplicación.
"""
import logging
import sys
from pathlib import Path

from backend.core.config import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"


def setup_logger(name: str = "tizon") -> logging.Logger:
    """
    Configura y retorna un logger con formato consistente.
    Logs van a archivo y consola.
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()
