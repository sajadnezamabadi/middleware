from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from utils.messages import ERROR_LOGIN_RATE_LIMIT_EXCEEDED, ERROR_RATE_LIMIT_EXCEEDED


def _get_ttl(key: str) -> int | None:
    try:
        ttl = cache.ttl(key)
    except (NotImplementedError, AttributeError):
        ttl = None
    return ttl



def _cache_key(namespace: str, identifier: str) -> str:
    return f"acl:{namespace}:{identifier}"


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int
    error_message: str | None = None


class LoginAttemptLimiter:
    """
    Simple per-username throttler to protect staff login endpoint.
    Uses Django cache backend; defaults work with locmem but scale with Redis.
    """

    def __init__(self) -> None:
        self.attempt_limit: int = getattr(settings, "ADMIN_LOGIN_ATTEMPT_LIMIT", 5)
        self.block_seconds: int = getattr(settings, "ADMIN_LOGIN_BLOCK_SECONDS", 300)

    def allow(self, username: str) -> RateLimitResult:
        if not username:
            # Empty usernames should not be throttled but we still protect against abuse
            username = "anonymous"

        key = _cache_key("login_attempts", username.lower())
        attempts = cache.get(key, 0)

        if attempts >= self.attempt_limit:
            ttl = _get_ttl(key)
            retry_after = ttl if ttl and ttl > 0 else self.block_seconds
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
                error_message=ERROR_LOGIN_RATE_LIMIT_EXCEEDED,
            )

        new_attempts = attempts + 1
        cache.set(key, new_attempts, timeout=self.block_seconds)
        remaining = max(self.attempt_limit - new_attempts, 0)
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            retry_after=self.block_seconds,
        )

    def reset(self, username: str) -> None:
        if username:
            cache.delete(_cache_key("login_attempts", username.lower()))


class AdminRequestRateLimiter:
    """
    Token-based rate limiter for admin API requests.
    Implements a fixed window counter backed by Django cache.
    """

    def __init__(self) -> None:
        self.request_limit: int = getattr(settings, "ADMIN_RATE_LIMIT_REQUESTS", 180)
        self.window_seconds: int = getattr(settings, "ADMIN_RATE_LIMIT_WINDOW_SECONDS", 60)

    def allow(self, token: str) -> RateLimitResult:
        if not token:
            token = "anonymous"

        key = _cache_key("admin_rate", token)
        window_start_key = f"{key}:start"

        current_window_start = cache.get(window_start_key)
        now = int(time.time())

        if current_window_start is None or now - current_window_start >= self.window_seconds:
            cache.set(window_start_key, now, timeout=self.window_seconds)
            cache.set(key, 1, timeout=self.window_seconds)
            remaining = self.request_limit - 1
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after=self.window_seconds,
            )

        count = cache.get(key, 0) + 1
        cache.set(key, count, timeout=self.window_seconds - (now - current_window_start))

        if count > self.request_limit:
            ttl = _get_ttl(key)
            retry_after = ttl if ttl and ttl > 0 else self.window_seconds
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
                error_message=ERROR_RATE_LIMIT_EXCEEDED,
            )

        remaining = max(self.request_limit - count, 0)
        ttl = _get_ttl(key)
        retry_after = ttl if ttl and ttl > 0 else self.window_seconds
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            retry_after=retry_after,
        )

