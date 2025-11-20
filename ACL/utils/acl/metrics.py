from __future__ import annotations

from typing import Dict, Iterable

from django.core.cache import cache
from django.conf import settings


_DEFAULT_TTL = getattr(settings, "ACL_METRIC_DEFAULT_TTL", 3600)


def _metric_key(name: str) -> str:
    return f"acl:metric:{name}"


def increment(name: str, amount: int = 1, ttl: int | None = None) -> None:
    """
    Increment a simple integer metric stored in cache.
    """
    key = _metric_key(name)
    ttl = ttl or _DEFAULT_TTL
    try:
        current = cache.get(key, 0)
        cache.set(key, int(current) + int(amount), timeout=ttl)
    except Exception:
        # Metrics must never break request flow
        return


def reset(name: str) -> None:
    """
    Reset a metric to zero.
    """
    try:
        cache.delete(_metric_key(name))
    except Exception:
        return


def snapshot(names: Iterable[str]) -> Dict[str, int]:
    """
    Return current values of given metric names.
    """
    result: Dict[str, int] = {}
    for name in names:
        try:
            result[name] = int(cache.get(_metric_key(name), 0))
        except Exception:
            result[name] = 0
    return result



