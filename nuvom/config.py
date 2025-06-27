# nuvom/config.py

import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root + .env path resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

# Load environment variables from .env file FIRST
# This ensures os.environ is populated before PydanticSettings tries to read it
load_dotenv(dotenv_path=ENV_PATH)

class NuvomSettings(BaseSettings):
    """
    Holds all environment-based configuration values for Nuvom.
    Uses Pydantic for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_prefix="NUVOM_",
        extra="ignore",
    )

    retry_delay_secs: int = 5
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    result_backend: Literal["file", "redis", "sqlite", "memory"] = "file"
    queue_backend: Literal["file", "redis", "sqlite", "memory"] = "file"
    serialization_backend: Literal["json", "msgpack", "pickle"] = "msgpack"

    queue_maxsize: int = 0
    max_workers: int = 4
    batch_size: int = 1
    job_timeout_secs: int = 1

    timeout_policy: Literal["fail", "retry", "ignore"] = "fail"
    
    def summary(self) -> dict:
        """Return key configuration values as a dictionary summary."""
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
        }

    def display(self) -> None:
        """Log the config summary to console."""
        from nuvom.log import logger  # Delayed import to avoid circular import
        logger.info("Nuvom Configuration:")
        for key, value in self.summary().items():
            logger.info(f"{key:20} = {value}")

# Internal global config state
_settings: NuvomSettings | None = None

def get_settings(force_reload: bool = False) -> NuvomSettings:
    """
    Get global Nuvom settings. Uses singleton pattern.
    Use `force_reload=True` to re-read from env.
    """
    global _settings
    if _settings is None or force_reload:
        _settings = NuvomSettings()

        # Setup logger immediately after settings load
        from nuvom.log import setup_logger
        setup_logger()

    return _settings

def override_settings(**kwargs):
    """
    Override settings (used in tests/dev only).
    Raises if the key is invalid.
    """
    global _settings
    if _settings is None:
        _settings = NuvomSettings()

    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)
        else:
            raise AttributeError(f"Invalid config key: '{key}'")
