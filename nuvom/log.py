# nuvom/log.py

from rich.console import Console
from rich.logging import RichHandler
import logging
import sys

# Global console instance for direct rich printing if needed
console = Console()

def setup_logger(level: str = "INFO") -> logging.Logger:
    """
    Set up and return the global logger instance.
    
    All logs go through rich and are colored with contextual info.
    """
    logger = logging.getLogger("nuvom")
    logger.setLevel(level.upper())

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        formatter = logging.Formatter(
            "[%(levelname)s] %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Global logger used across the project
logger = setup_logger()
