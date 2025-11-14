from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

from utils.acl.engine import ACLDecisionEngine
from utils.models import Endpoint, MethodEncoding

# TODO : remove token from cache and read from permission
def _token_cache_key(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"acl:routes:{digest}"


def _token_ttl_seconds() -> int:
    lifetime = getattr(settings, "JWT_ACCESS_TOKEN_LIFETIME", None)
    if lifetime is not None:
        try:
            seconds = int(lifetime.total_seconds())
            if seconds > 0:
                return seconds
        except AttributeError:
            pass
    return int(getattr(settings, "JWT_ACCESS_TOKEN_LIFETIME_SECONDS", 900))


def build_routes_for_token(staff, token: str) -> List[Dict[str, Any]]:
    """
    Calculate accessible routes for a freshly issued access token and cache them.
    Returns a list of dictionaries containing path, method, encoded method and metadata.
    """
    engine = ACLDecisionEngine()
    routes: List[Dict[str, Any]] = []

    endpoints = Endpoint.objects.filter(is_active=True)
    for endpoint in endpoints:
        payload = {
            "id": str(endpoint.pk),
            "service": endpoint.service,
            "path_pattern": endpoint.path_pattern,
            "method": endpoint.method,
            "action": endpoint.action,
        }

        if not engine.is_allowed(staff, payload):
            continue

        encoding = MethodEncoding.objects.filter(method__iexact=endpoint.method).first()
        encoded_method = encoding.encoded if encoding else ""

        routes.append(
            {
                "path": endpoint.path_pattern,
                "method": endpoint.method,
                "encoded_method": encoded_method,
                "service": endpoint.service,
                "endpoint_id": str(endpoint.pk),
            }
        )

    cache.set(_token_cache_key(token), routes, timeout=_token_ttl_seconds())
    return routes


def get_routes_for_token(token: str) -> Optional[List[Dict[str, Any]]]:
    return cache.get(_token_cache_key(token))


def clear_routes_for_token(token: str) -> None:
    cache.delete(_token_cache_key(token))

