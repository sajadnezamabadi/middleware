from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from django.conf import settings
from django.core.cache import cache


_METRIC_PREFIX = "acl:metrics:"


def _key(name: str) -> str:
    return f"{_METRIC_PREFIX}{name}"


def increment(metric: str, amount: int = 1, ttl: int | None = None) -> None:
    """
    Increment a counter stored in cache. Works with locmem and Redis backends.
    """
    key = _key(metric)
    if ttl is None:
        ttl = getattr(settings, "ACL_METRIC_DEFAULT_TTL", 3600)
    try:
        cache.incr(key, amount)
        if ttl:
            try:
                cache.touch(key, ttl)
            except (NotImplementedError, AttributeError):
                if ttl:
                    cache.set(key, cache.get(key), timeout=ttl)
    except (ValueError, NotImplementedError, AttributeError):
        # Fallback: cache.incr may fail if key does not exist or backend lacks incr.
        current = cache.get(key, 0)
        cache.set(key, current + amount, timeout=ttl)


def reset(metric: str) -> None:
    cache.delete(_key(metric))


def snapshot(metrics: list[str]) -> Dict[str, int]:
    data: Dict[str, int] = {}
    for metric in metrics:
        value = cache.get(_key(metric), 0)
        data[metric] = int(value or 0)
    return data

