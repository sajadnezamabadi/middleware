from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from utils.messages import (
    ERROR_LOGIN_RATE_LIMIT_EXCEEDED,
    ERROR_RATE_LIMIT_EXCEEDED,
)


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: int = 0
    error_message: str | None = None


class LoginAttemptLimiter:
    """
    Simple login attempt limiter per username.
    Uses cache counter with expiry window.
    """

    def __init__(self) -> None:
        self.limit = getattr(settings, "ADMIN_LOGIN_ATTEMPT_LIMIT", 5)
        self.block_seconds = getattr(settings, "ADMIN_LOGIN_BLOCK_SECONDS", 5 * 60)

    def _key(self, username: str) -> str:
        return f"acl:login_attempts:{username}"

    def allow(self, username: str) -> RateLimitResult:
        key = self._key(username)
        attempts = cache.get(key, 0)
        if attempts >= self.limit:
            # Remaining TTL approximates retry_after
            ttl = cache.ttl(key)
            retry_after = int(ttl) if isinstance(ttl, int) and ttl > 0 else self.block_seconds
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                error_message=ERROR_LOGIN_RATE_LIMIT_EXCEEDED,
            )

        # Increment and (re)set expiry
        cache.set(key, int(attempts) + 1, timeout=self.block_seconds)
        return RateLimitResult(allowed=True)

    def reset(self, username: str) -> None:
        cache.delete(self._key(username))


class AdminRequestRateLimiter:
    """
    Request-based limiter for admin APIs.
    """

    def __init__(self) -> None:
        self.limit = getattr(settings, "ADMIN_RATE_LIMIT_REQUESTS", 180)
        self.window = getattr(settings, "ADMIN_RATE_LIMIT_WINDOW_SECONDS", 60)

    def _key(self, identifier: str) -> str:
        return f"acl:admin_rate:{identifier}"

    def allow(self, identifier: str) -> RateLimitResult:
        key = self._key(identifier)
        count = cache.get(key, 0)
        if count >= self.limit:
            ttl = cache.ttl(key)
            retry_after = int(ttl) if isinstance(ttl, int) and ttl > 0 else self.window
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                error_message=ERROR_RATE_LIMIT_EXCEEDED,
            )

        cache.set(key, int(count) + 1, timeout=self.window)
        return RateLimitResult(allowed=True)



