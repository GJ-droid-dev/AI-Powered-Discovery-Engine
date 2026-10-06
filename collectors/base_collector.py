"""Abstract base class for all data source collectors.

Provides:
    - Abstract collect() interface
    - Rate-limiting decorator
    - Retry with exponential backoff (3 retries, 1s/2s/4s)
"""

from __future__ import annotations

import time
import functools
import logging
from abc import ABC, abstractmethod
from typing import Any, Iterator

from core.errors import RetryableError, SourceDegradedError


logger = logging.getLogger("discovery_engine")


def rate_limit(calls_per_second: float = 1.0):
    """Decorator that enforces a minimum delay between calls."""
    min_interval = 1.0 / calls_per_second

    def decorator(func):
        last_call_time = [0.0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call_time[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call_time[0] = time.time()
            return func(*args, **kwargs)

        return wrapper
    return decorator


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator that retries a function with exponential backoff on RetryableError."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RetryableError as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                            f"(waiting {delay}s): {e}",
                            extra={"stage": "collector"},
                        )
                        time.sleep(delay)
                    else:
                        raise
            raise last_exception  # type: ignore

        return wrapper
    return decorator


class BaseCollector(ABC):
    """Abstract base class for data source collectors.

    Each collector must implement:
        - collect() → Iterator of raw records (dicts)

    Raw records are source-specific dicts. The DataNormalizer handles
    conversion to UnifiedRecord.
    """

    def __init__(self, source_type: str, params: dict[str, Any] | None = None):
        self.source_type = source_type
        self.params = params or {}
        self.logger = logging.getLogger("discovery_engine")

    @abstractmethod
    def collect(self) -> Iterator[dict[str, Any]]:
        """Yield raw records from this source.

        Each record is a dict with source-specific fields.
        The normalizer will map these to UnifiedRecord.

        Yields:
            dict with at minimum: {"raw_text": str}
        """
        ...

    def _log_progress(self, count: int, source: str) -> None:
        """Log collection progress every 100 records."""
        if count % 100 == 0 and count > 0:
            self.logger.info(
                f"Collected {count} records from {source}",
                extra={"stage": "collector", "source_type": self.source_type},
            )
