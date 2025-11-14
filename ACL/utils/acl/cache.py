from __future__ import annotations

import json
from typing import Any, Optional

import redis
from django.conf import settings
from redis import RedisError


class RedisCache:
    def __init__(self) -> None:
        url = getattr(settings, "REDIS_URL", None)
        if not url:
            host = getattr(settings, "REDIS_HOST", "127.0.0.1")
            port = getattr(settings, "REDIS_PORT", "6379")
            db = getattr(settings, "REDIS_DB", "0")
            username = getattr(settings, "REDIS_USERNAME", None)
            password = getattr(settings, "REDIS_PASSWORD", None)
            credentials = ""
            if username:
                credentials = f"{username}:{password or ''}@"
            elif password:
                credentials = f":{password}@"
            url = f"redis://{credentials}{host}:{port}/{db}"

        self.client = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except RedisError:
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        try:
            self.client.set(key, value, ex=ex)
        except RedisError:
            pass

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except RedisError:
            pass

    def get_json(self, key: str) -> Optional[Any]:
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> None:
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError):
            return
        self.set(key, payload, ex=ex)

