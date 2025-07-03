# nuvom/policies/retry.py

"""
RetryPolicy interface and default implementations.

Responsible for deciding:
    - Should a retry occur?
    - How long to wait before retrying?

Attached to a JobRunner to guide retry loop behavior.
"""

from abc import ABC, abstractmethod
from typing import Optional
import time
import random


class RetryPolicy(ABC):
    """Interface for controlling retry behavior in job runners."""

    @abstractmethod
    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        """Return True if the job should be retried."""
        ...

    @abstractmethod
    def get_delay(self, attempts_done: int) -> float:
        """Return how long (in seconds) to wait before the next retry."""
        ...


class FixedRetry(RetryPolicy):
    """
    Retry up to `max_attempts`, waiting `interval` seconds between tries.
    """

    def __init__(self, max_attempts: int, interval: float = 0.0) -> None:
        self.max_attempts = max_attempts
        self.interval = interval

    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        return attempts_done < self.max_attempts

    def get_delay(self, attempts_done: int) -> float:
        return self.interval


class ExponentialBackoff(RetryPolicy):
    """
    Retry with exponential backoff and optional jitter.

    Example:
        base = 0.5, factor = 2.0, jitter = 0.2
        Delays → 0.5s, 1.0s, 2.0s, 4.0s (+ jitter)
    """

    def __init__(
        self,
        max_attempts: int,
        base: float = 0.5,
        factor: float = 2.0,
        jitter: float = 0.1,
    ) -> None:
        self.max_attempts = max_attempts
        self.base = base
        self.factor = factor
        self.jitter = jitter

    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        return attempts_done < self.max_attempts

    def get_delay(self, attempts_done: int) -> float:
        delay = self.base * (self.factor ** attempts_done)
        if self.jitter:
            delay += random.uniform(-self.jitter, self.jitter)
        return max(0.0, delay)
