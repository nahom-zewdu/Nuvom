# nuvom/config.py

"""
Central configuration loader for Nuvom, powered by:
- dotenv for `.env` injection
- Pydantic for strict validation and schema enforcement

Supports:
- Static and plugin-defined result, queue, and scheduler backends
- Windows-friendly SQLite path handling
- High-level summary and display helpers for logging and debugging
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------------------------------------------------ #
# Constants & environment setup
# ------------------------------------------------------------------ #
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
PROJECT_ENV_PATH = Path(".env")

# Pre-load environment variables:
# 1. Try .env in the current working directory (project root in most cases)
# 2. Fallback to the internal .env for local dev
if not load_dotenv(override=True):  # returns False if no .env was found
    load_dotenv(dotenv_path=ENV_PATH, override=True)

# Supported built-in backends.
_BUILTIN_BACKENDS = {"file", "redis", "sqlite", "memory"}


class NuvomSettings(BaseSettings):
    """
    Global Nuvom configuration.

    Values are loaded from:
    - Environment variables prefixed with `NUVOM_`
    - Defaults defined in this class

    Attributes
    ----------
    retry_delay_secs : int
        Delay before retrying failed jobs (seconds).
    environment : {"dev","prod","test"}
        Deployment environment identifier.
    log_level : {"DEBUG","INFO","WARNING","ERROR"}
        Global log verbosity.
    result_backend : str
        Backend to store job results (built-in or plugin).
    queue_backend : str
        Backend to enqueue jobs (built-in or plugin).
    scheduler_backend : str
        Backend used by the scheduler (built-in or plugin).
    serialization_backend : {"json","msgpack","pickle"}
        Format for job serialization.
    queue_maxsize : int
        Max in-memory queue size (0 = unlimited).
    max_workers : int
        Maximum concurrent worker threads.
    batch_size : int
        Number of jobs fetched in each polling batch.
    job_timeout_secs : int
        Timeout for each job execution.
    timeout_policy : {"fail","retry","ignore"}
        Behavior when job exceeds `job_timeout_secs`.
    sqlite_db_path : Path
        Path for SQLite result database.
    sqlite_queue_path : Path
        Path for SQLite queue database.
    prometheus_port : int
        Port for Prometheus metrics exporter.
    """

    # Prefer project-level .env, fallback to internal one for dev
    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH if PROJECT_ENV_PATH.exists() else ENV_PATH,
        env_prefix="NUVOM_",
        extra="ignore",
    )

    # ---------------- Core ---------------- #
    retry_delay_secs: int = 5
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    result_backend: Annotated[
        str,
        Field(description="Backend used to store job results (built-in or plugin)")
    ] = "sqlite"

    queue_backend: Annotated[
        str,
        Field(description="Backend used to enqueue jobs (built-in or plugin)")
    ] = "sqlite"

    scheduler_backend: Annotated[
        str,
        Field(description="Backend used to store and manage scheduled jobs (built-in or plugin)")
    ] = "sqlite"

    serialization_backend: Literal["json", "msgpack", "pickle"] = "msgpack"

    # ---------------- Worker / Queue ---------------- #
    queue_maxsize: int = 0
    max_workers: int = 4
    batch_size: Annotated[int, Field(ge=1)] = 1
    job_timeout_secs: int = 1
    timeout_policy: Literal["fail", "retry", "ignore"] = "fail"

    # ---------------- SQLite ---------------- #
    sqlite_db_path: Path = ".nuvom/result.db"
    sqlite_queue_path: Path = ".nuvom/queue.db"

    # ---------------- Monitoring ---------------- #
    prometheus_port: Annotated[int, Field(ge=1, le=65535)] = 9150

    # ---------------- Validators ---------------- #
    @staticmethod
    def _validate_backend(v: str, field_name: str) -> str:
        """Internal helper to validate or warn for plugin-defined backends."""
        import logging
        if v not in _BUILTIN_BACKENDS:
            logging.getLogger(__name__).debug(
                "Using plugin-defined %s backend: %r", field_name, v
            )
        return v

    @field_validator("result_backend", mode="before")
    @classmethod
    def _validate_result_backend(cls, v: str) -> str:
        return cls._validate_backend(v, "result")

    @field_validator("queue_backend", mode="before")
    @classmethod
    def _validate_queue_backend(cls, v: str) -> str:
        return cls._validate_backend(v, "queue")

    @field_validator("scheduler_backend", mode="before")
    @classmethod
    def _validate_scheduler_backend(cls, v: str) -> str:
        return cls._validate_backend(v, "scheduler")

    @field_validator("sqlite_db_path", mode="before")
    @classmethod
    def _coerce_sqlite_path(cls, v) -> Path:
        return Path(v) if not isinstance(v, Path) else v

    @field_validator("sqlite_queue_path", mode="before")
    @classmethod
    def _coerce_sqlite_queue_path(cls, v) -> Path:
        return Path(v) if not isinstance(v, Path) else v

    # ---------------- Developer helpers ---------------- #
    def summary(self) -> dict:
        """
        Return a dict of high-level config values for quick display.
        Useful for debugging or logging startup configuration.
        """
        return {
            "env": self.environment,
            "log_level": self.log_level,
            "workers": self.max_workers,
            "batch_size": self.batch_size,
            "timeout": self.job_timeout_secs,
            "queue_size": self.queue_maxsize,
            "queue_backend": self.queue_backend,
            "result_backend": self.result_backend,
            "scheduler_backend": self.scheduler_backend,
            "serialization_backend": self.serialization_backend,
            "timeout_policy": self.timeout_policy,
            "sqlite_db": str(self.sqlite_db_path),
            "sqlite_queue": str(self.sqlite_queue_path),
            "prometheus_port": self.prometheus_port,
        }

    def display(self) -> None:
        """
        Pretty-print the current configuration to the central logger.
        """
        from nuvom.log import get_logger
        logger = get_logger()
        logger.info("Nuvom Configuration:")
        for k, v in self.summary().items():
            logger.info(f"{k:20} = {v}")


# ------------------------------------------------------------------ #
# Singleton accessor
# ------------------------------------------------------------------ #
_settings: NuvomSettings | None = None
_settings_lock = threading.Lock()


def get_settings(force_reload: bool = False) -> NuvomSettings:
    """
    Return the global settings singleton.

    Parameters
    ----------
    force_reload : bool, default False
        Forces re-loading of settings, useful for testing or runtime updates.

    Returns
    -------
    NuvomSettings
        Singleton instance of the configuration.
    """
    global _settings
    if _settings is None or force_reload:
        with _settings_lock:
            if _settings is None or force_reload:
                _settings = NuvomSettings()
    return _settings


def override_settings(**kwargs):
    """
    Deprecated: Mutate the global settings singleton for testing.

    Prefer:
    -------
    - Initializing a fresh NuvomSettings object with overrides, or
    - Using dependency injection in components for better isolation.
    """
    s = get_settings()
    for key, value in kwargs.items():
        if hasattr(s, key):
            setattr(s, key, value)
        else:
            raise AttributeError(f"Invalid config key: '{key}'")
