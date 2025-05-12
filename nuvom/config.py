# Env variable parsing or settings config (threads, batching, etc.)

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class NuvomSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NUVOM_")

    # General settings
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # Backed-result storage
    result_backend: Literal["file", "redis", "sqlite", "memory"] = "memory"  # default

    # Queue settings
    queue_backend: Literal["file", "redis", "sqlite", "memory"] = "file"
    queue_maxsize: int = 0  # 0 = infinite

    # serializer settings
    serialization_backend: Literal["json", "msgpack", "pickle"] = "msgpack"
    
    # Worker-related
    max_workers: int = 4
    batch_size: int = 1
    job_timeout_secs: int = 60

    def summary(self):
        return {
            "env": self.environment,
            "log_level": self.log_level,
            "workers": self.max_workers,
            "batch_size": self.batch_size,
            "timeout": self.job_timeout_secs,
            "queue_size": self.queue_maxsize,
            "result_backend": self.result_backend
        }


# Singleton-ish config access
_settings = None


def get_settings() -> NuvomSettings:
    global _settings
    if _settings is None:
        _settings = NuvomSettings()
    return _settings
