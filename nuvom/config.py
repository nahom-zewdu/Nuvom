# nuvom/config.py

"""
Configuration loader (dotenv + Pydantic).

Supports:
• Static and plugin-defined result/queue backends
• Windows-friendly SQLite path handling
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------------------------------------------------#
# Constants & .env loading
# ------------------------------------------------------------------#
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

# Pre-load .env so child processes inherit the variables.
# (Remove this if you *only* need Pydantic’s env_file behaviour.)
load_dotenv(dotenv_path=ENV_PATH, override=False)

_BUILTIN_BACKENDS = {"file", "redis", "sqlite", "memory"}

# ------------------------------------------------------------------#
# Settings definition
# ------------------------------------------------------------------#
class NuvomSettings(BaseSettings):
    """
    Environment-driven settings validated by Pydantic.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_prefix="NUVOM_",
        extra="ignore",
    )

    # ---------- Core ----------
    retry_delay_secs: int = 5
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    result_backend: Annotated[
        str,
        Field(description="Backend used to store job results (built-in or plugin)"),
    ] = "file"

    queue_backend: Literal["file", "redis", "sqlite", "memory"] = "file"
    serialization_backend: Literal["json", "msgpack", "pickle"] = "msgpack"

    # ---------- Worker / Queue ----------
    queue_maxsize: int = 0
    max_workers: int = 4
    batch_size: Annotated[int, Field(ge=1)] = 1
    job_timeout_secs: int = 1
    timeout_policy: Literal["fail", "retry", "ignore"] = "fail"

    # ---------- SQLite ----------
    sqlite_db_path: Path = ".nuvom/nuvom.db"
    
    # ---------- Monitoring ----------
    prometheus_port: Annotated[int, Field(ge=1, le=65535)] = 9150

    # ---------- Validators ----------
    @field_validator("result_backend")
    @classmethod
    def _warn_if_plugin_backend(cls, v: str) -> str:  # noqa: D401
        if v not in _BUILTIN_BACKENDS:
            import logging

            logging.getLogger(__name__).debug(
                "Using plugin-defined result backend: %r", v
            )
        return v

    @field_validator("sqlite_db_path", mode="before")
    @classmethod
    def _coerce_sqlite_path(cls, v) -> Path:  # noqa: D401
        """Ensure the SQLite path is always a Path object."""
        return Path(v) if not isinstance(v, Path) else v

    # ---------- Developer helpers ----------
    def summary(self) -> dict:
        """Return a dict of high-level config values for quick display."""
        return {
            "env": self.environment,
            "log_level": self.log_level,
            "workers": self.max_workers,
            "batch_size": self.batch_size,
            "timeout": self.job_timeout_secs,
            "queue_size": self.queue_maxsize,
            "queue_backend": self.queue_backend,
            "result_backend": self.result_backend,
            "serialization_backend": self.serialization_backend,
            "timeout_policy": self.timeout_policy,
            "sqlite_db": str(self.sqlite_db_path),
        }

    def display(self) -> None:
        """Pretty-print the current configuration via the central logger."""
        from nuvom.log import get_logger

        logger = get_logger()
        logger.info("Nuvom Configuration:")
        for k, v in self.summary().items():
            logger.info(f"{k:20} = {v}")


# ------------------------------------------------------------------#
# Singleton access helpers
# ------------------------------------------------------------------#
_settings: NuvomSettings | None = None
_settings_lock = threading.Lock()


def get_settings(force_reload: bool = False) -> NuvomSettings:
    """
    Return the global settings singleton.

    A threading.Lock guards against double-initialisation in worker threads.
    """
    global _settings
    if _settings is None or force_reload:
        with _settings_lock:
            if _settings is None or force_reload:
                _settings = NuvomSettings()
    return _settings


def override_settings(**kwargs):
    """
    **Deprecated test helper.**

    Mutates the global settings instance in-place — use with caution.
    Prefer injecting a fresh NuvomSettings into the component under test.
    """
    s = get_settings()
    for key, value in kwargs.items():
        if hasattr(s, key):
            setattr(s, key, value)
        else:
            raise AttributeError(f"Invalid config key: '{key}'")
