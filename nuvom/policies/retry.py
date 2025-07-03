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
import random


class RetryPolicy(ABC):
    """Interface for controlling retry behavior in job runners."""

    @abstractmethod
    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        """
        Determine whether a retry should be attempted.

        Args:
            attempts_done: Number of attempts already performed (starting at 0).
            error: The exception that caused the failure.

        Returns:
            True if the job should be retried, False otherwise.
        """
        ...

    @abstractmethod
    def get_delay(self, attempts_done: int) -> float:
        """
        Compute the delay in seconds before the next retry attempt.

        Args:
            attempts_done: Number of attempts already performed (starting at 0).

        Returns:
            Delay in seconds (non-negative float).
        """
        ...


class FixedRetry(RetryPolicy):
    """
    Retry a fixed number of times with a constant delay between attempts.

    Args:
        max_attempts: Maximum number of attempts including the first try.
        interval: Fixed delay in seconds between retries.
    """

    def __init__(self, max_attempts: int = 3, interval: float = 0.0):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if interval < 0:
            raise ValueError("interval must be >= 0")
        self.max_attempts = max_attempts
        self.interval = interval

    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        return attempts_done + 1 < self.max_attempts

    def get_delay(self, attempts_done: int) -> float:
        return self.interval


class ExponentialBackoff(RetryPolicy):
    """
    Retry with exponential backoff delay and optional jitter.

    Args:
        max_attempts: Maximum number of attempts including the first try.
        base: Base delay in seconds.
        factor: Exponential growth factor.
        max_delay: Maximum delay in seconds.
        jitter: Max random jitter (+/- seconds) added to the delay.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base: float = 0.5,
        factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: float = 0.1,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if base <= 0:
            raise ValueError("base must be > 0")
        if factor < 1:
            raise ValueError("factor must be >= 1")
        if max_delay < base:
            raise ValueError("max_delay must be >= base")
        if jitter < 0:
            raise ValueError("jitter must be >= 0")

        self.max_attempts = max_attempts
        self.base = base
        self.factor = factor
        self.max_delay = max_delay
        self.jitter = jitter

    def should_retry(self, attempts_done: int, error: Exception) -> bool:
        return attempts_done + 1 < self.max_attempts

    def get_delay(self, attempts_done: int) -> float:
        delay = self.base * (self.factor ** attempts_done)
        if self.jitter:
            delay += random.uniform(-self.jitter, self.jitter)
        delay = max(0.0, delay)
        return min(delay, self.max_delay)
