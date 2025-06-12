import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root + .env path resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

class NuvomSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_prefix="NUVOM_",
        extra="ignore",
    )

    environment: Literal["dev", "prod", "test"] = Field("dev", validation_alias="ENVIRONMENT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO", validation_alias="LOG_LEVEL")

    result_backend: Literal["file", "redis", "sqlite", "memory"] = Field("file", validation_alias="RESULT_BACKEND")
    queue_backend: Literal["file", "redis", "sqlite", "memory"] = Field("file", validation_alias="QUEUE_BACKEND")
    serialization_backend: Literal["json", "msgpack", "pickle"] = Field("msgpack", validation_alias="SERIALIZATION_BACKEND")

    queue_maxsize: int = Field(0, validation_alias="QUEUE_MAXSIZE")
    max_workers: int = Field(4, validation_alias="MAX_WORKERS")
    batch_size: int = Field(1, validation_alias="BATCH_SIZE")
    job_timeout_secs: int = Field(60, validation_alias="JOB_TIMEOUT_SECS")

    def summary(self) -> dict:
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
        }

    def display(self) -> None:
        print("Nuvom Configuration:")
        for key, value in self.summary().items():
            print(f"{key:20} = {value}")

# Internal global config state
_settings: NuvomSettings | None = None

def get_settings(force_reload: bool = False) -> NuvomSettings:
    """Get global Nuvom settings. Use `force_reload=True` only when needed."""
    global _settings
    if _settings is None or force_reload:
        print(f"[debug] Loading settings from: {ENV_PATH}")
        _settings = NuvomSettings()
    return _settings

def override_settings(**kwargs):
    """Override config values for tests or runtime tweaks. Avoid in prod logic."""
    global _settings
    if _settings is None:
        _settings = NuvomSettings()

    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)
        else:
            raise AttributeError(f"Invalid config key: '{key}'")
