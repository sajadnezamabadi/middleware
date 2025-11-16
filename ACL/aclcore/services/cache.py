from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings
from django.core.cache import cache


class CacheService:
    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        self.ttl_seconds = ttl_seconds or getattr(settings, "ACLCORE_CACHE_TTL_SECONDS", 3600)

    @staticmethod
    def _key(application: str | None, user_id: str, method: str, normalized_path: str) -> str:
        app = application or "default"
        return f"aclcore:cache:{app}:{user_id}:{method}:{normalized_path}"

    def get(self, application: str | None, user_id: str, method: str, normalized_path: str) -> Optional[bool]:
        return cache.get(self._key(application, user_id, method, normalized_path))

    def set(self, application: str | None, user_id: str, method: str, normalized_path: str, allowed: bool) -> None:
        cache.set(self._key(application, user_id, method, normalized_path), allowed, timeout=self.ttl_seconds)


