"""
Rate limiter for Riot Games API dev key.
Dev key limits: 20 req/s, 100 req/2min.
We enforce a conservative 90 req/120s + 1 req/s.
"""
from __future__ import annotations

import time
import threading
from collections import deque
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class RiotRateLimiter:
    """
    Token-bucket style rate limiter respecting Riot dev key constraints.
    Thread-safe — safe to use from a single watcher thread.
    """

    def __init__(
        self,
        calls_per_window: int = 90,
        window_seconds: int = 120,
        min_interval: float = 1.05,  # ~1 req/s with margin
    ):
        self.calls_per_window = calls_per_window
        self.window_seconds = window_seconds
        self.min_interval = min_interval

        self._lock = threading.Lock()
        self._call_times: deque[float] = deque()
        self._last_call: float = 0.0

    def wait(self) -> None:
        """Block until a request can be safely fired."""
        with self._lock:
            now = time.monotonic()

            # Enforce minimum interval between calls
            since_last = now - self._last_call
            if since_last < self.min_interval:
                sleep_time = self.min_interval - since_last
                logger.debug(f"Rate limiter: sleeping {sleep_time:.2f}s (min interval)")
                time.sleep(sleep_time)
                now = time.monotonic()

            # Enforce sliding window
            window_start = now - self.window_seconds
            while self._call_times and self._call_times[0] < window_start:
                self._call_times.popleft()

            if len(self._call_times) >= self.calls_per_window:
                oldest = self._call_times[0]
                sleep_time = oldest + self.window_seconds - now + 0.1
                if sleep_time > 0:
                    logger.warning(
                        f"Rate limit window full ({self.calls_per_window} calls). "
                        f"Sleeping {sleep_time:.1f}s"
                    )
                    time.sleep(sleep_time)
                    now = time.monotonic()

            self._call_times.append(now)
            self._last_call = now

    def __call__(self, fn: Callable) -> Callable:
        """Decorator usage: @rate_limiter"""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.wait()
            return fn(*args, **kwargs)
        return wrapper


# Singleton instance used across the project
rate_limiter = RiotRateLimiter()
