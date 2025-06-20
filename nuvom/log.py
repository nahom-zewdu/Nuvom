# nuvom/log.py

from rich.console import Console
from rich.logging import RichHandler
import logging
import sys

# Global console instance for optional direct Rich output
console = Console()

def setup_logger(level: str | None = None) -> logging.Logger:
    """
    Set up and return the global logger instance using RichHandler.
    
    - Respects the level set in Nuvom config (NUVOM_LOG_LEVEL)
    - Enables markup, rich tracebacks, and disables noisy paths
    """
    from nuvom.config import get_settings  # Delayed import to avoid circularity
    
    config = get_settings()
    level = level or config.log_level

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
