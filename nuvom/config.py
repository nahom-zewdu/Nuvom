# nuvom/config.py

"""
Configuration loader (dot-env + Pydantic).

Supports:
• Static + plugin-defined result backends
• SQLite database location via `sqlite_db_path`
"""

import os
from pathlib import Path
from typing import Literal, Annotated

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------------------------------------------------#
# Constants & Env Loading
# ------------------------------------------------------------------#
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)  # Populate os.environ

_BUILTIN_BACKENDS = {"file", "redis", "sqlite", "memory"}

# ------------------------------------------------------------------#
# Settings Definition
# ------------------------------------------------------------------#
class NuvomSettings(BaseSettings):
    """
    Environment-driven settings, validated and type-checked by Pydantic.
    Supports plugin result/queue backends.
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
        Field(description="Backend to store job results (built-in or plugin-defined)")
    ] = "file"

    queue_backend: Literal["file", "redis", "sqlite", "memory"] = "file"
    serialization_backend: Literal["json", "msgpack", "pickle"] = "msgpack"

    # ---------- Worker / Queue ----------
    queue_maxsize: int = 0
    max_workers: int = 4
    batch_size: int = 1
    job_timeout_secs: int = 1
    timeout_policy: Literal["fail", "retry", "ignore"] = "fail"

    # ---------- SQLite ----------
    sqlite_db_path: Path = ".nuvom/nuvom.db"

    # ---------- Validator ----------
    @field_validator("result_backend")
    @classmethod
    def _warn_if_plugin_backend(cls, v: str) -> str:
        if v not in _BUILTIN_BACKENDS:
            from nuvom.log import logger
            logger.debug("[Config] Using plugin-defined result backend: %r", v)
        return v

    # ---------- Developer Display ----------
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
        from nuvom.log import logger
        logger.info("Nuvom Configuration:")
        for k, v in self.summary().items():
            logger.info(f"{k:20} = {v}")


# ------------------------------------------------------------------#
# Singleton Access
# ------------------------------------------------------------------#
_settings: NuvomSettings | None = None


def get_settings(force_reload: bool = False) -> NuvomSettings:
    """Return the global settings singleton (reload if requested)."""
    global _settings
    if _settings is None or force_reload:
        _settings = NuvomSettings()
        from nuvom.log import setup_logger
        setup_logger()
    return _settings


def override_settings(**kwargs):
    """Utility for tests to override settings on the fly."""
    s = get_settings()
    for key, value in kwargs.items():
        if hasattr(s, key):
            setattr(s, key, value)
        else:
            raise AttributeError(f"Invalid config key: '{key}'")
