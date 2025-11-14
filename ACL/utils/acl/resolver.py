from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.apps import apps
from django.conf import settings
from django.urls import Resolver404, resolve

from .cache import RedisCache
from .exceptions import EndpointNotFound

logger = logging.getLogger(__name__)


def _load_endpoint_model():
    app_label = getattr(settings, "ACL_ENDPOINT_APP", "utils")
    model_name = getattr(settings, "ACL_ENDPOINT_MODEL", "Endpoint")
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        logger.error("Endpoint model %s.%s not found", app_label, model_name)
        return None


EndpointModel = _load_endpoint_model()


class EndpointResolver:
    """
    Resolve incoming requests to the corresponding Endpoint instance (or metadata).
    """

    def __init__(self, cache: Optional[RedisCache] = None) -> None:
        self.cache = cache or RedisCache()
        self.ttl = getattr(settings, "ACL_CACHE_TTL", 3600)

    def resolve(self, request) -> Dict[str, Any]:
        method = request.method.upper()
        path = request.path_info

        route_name = self._resolve_route_name(path)
        if route_name:
            cached = self._get_cached_by_route(method, route_name)
            if cached:
                return cached

        endpoint_payload = self._resolve_from_database(method, route_name, path)
        if endpoint_payload:
            return endpoint_payload

        raise EndpointNotFound(f"Endpoint not found for method={method} path={path}")

    def _resolve_route_name(self, path: str) -> Optional[str]:
        try:
            match = resolve(path)
        except Resolver404:
            return None
        return match.view_name or match.url_name or match.app_name

    def _cache_key_for_route(self, method: str, route_name: str) -> str:
        return f"endpoint:route:{method}:{route_name}"

    def _get_cached_by_route(self, method: str, route_name: str) -> Optional[Dict[str, Any]]:
        payload = self.cache.get_json(self._cache_key_for_route(method, route_name))
        if payload:
            return payload
        return None

    def _resolve_from_database(self, method: str, route_name: Optional[str], path: str) -> Optional[Dict[str, Any]]:
        if EndpointModel is None:
            return None

        queryset = EndpointModel.objects.filter(method=method, is_active=True)
        if route_name:
            endpoint = queryset.filter(path_pattern=route_name).first()
            if endpoint:
                payload = self._make_payload(endpoint)
                self.cache.set_json(self._cache_key_for_route(method, route_name), payload, ex=self.ttl)
                return payload

        for endpoint in queryset:
            if self._simple_match(endpoint.path_pattern, path):
                payload = self._make_payload(endpoint)
                cache_key = f"endpoint:id:{endpoint.pk}"
                self.cache.set_json(cache_key, payload, ex=self.ttl)
                if route_name:
                    self.cache.set_json(self._cache_key_for_route(method, route_name), payload, ex=self.ttl)
                return payload

        return None

    def _simple_match(self, pattern: str, path: str) -> bool:
        if "{" in pattern and "}" in pattern:
            pattern_segments = [segment for segment in pattern.strip("/").split("/") if segment]
            path_segments = [segment for segment in path.strip("/").split("/") if segment]
            if len(pattern_segments) != len(path_segments):
                return False
            for p_seg, a_seg in zip(pattern_segments, path_segments):
                if p_seg.startswith("{") and p_seg.endswith("}"):
                    continue
                if p_seg != a_seg:
                    return False
            return True
        return pattern.rstrip("/") == path.rstrip("/")

    def _make_payload(self, endpoint: Any) -> Dict[str, Any]:
        return {
            "id": str(endpoint.pk),
            "service": endpoint.service,
            "path_pattern": endpoint.path_pattern,
            "method": endpoint.method,
            "action": endpoint.action,
        }

