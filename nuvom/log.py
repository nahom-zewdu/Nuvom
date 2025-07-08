# nuvom/logging.py
from __future__ import annotations
import logging
import threading
from rich.console import Console
from rich.logging import RichHandler
from typing import Optional

_console = Console()
_lock = threading.Lock()
_logger: Optional[logging.Logger] = None

def setup_logger(level: str = "INFO") -> logging.Logger:
    """Configure the global 'nuvom' logger once. Safe to call repeatedly."""
    global _logger
    with _lock:
        if _logger is not None:
            return _logger                        # already configured

        logger = logging.getLogger("nuvom")
        logger.setLevel(level.upper())

        handler = RichHandler(
            console=_console,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)

        _logger = logger
        return logger

def get_logger(level: str | None = None) -> logging.Logger:
    """Return the configured logger, initialising it if necessary."""
    return _logger or setup_logger(level or "INFO")
