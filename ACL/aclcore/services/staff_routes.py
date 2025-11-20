from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from django.conf import settings
from django.core.cache import cache

from aclcore.models import (
    ACLApplication,
    ACLRoleRoutePermission,
    ACLRoute,
    ACLUserRole,
)


def _routes_cache_key(user_id: str, application: Optional[str]) -> str:
    app = application or getattr(settings, "ACLCORE_DEFAULT_APPLICATION", "") or "default"
    return f"aclcore:routes:{app}:{user_id}"


def _encode_method(method: str) -> str:
    """
    Optional compact encoding for HTTP methods.
    Kept simple; callers can ignore if not needed.
    """
    mapping = {
        "GET": "R",
        "POST": "C",
        "PUT": "U",
        "PATCH": "U",
        "DELETE": "D",
    }
    return mapping.get(method.upper(), method.upper())


def build_routes_for_user(user_id: str, application: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Build and cache list of allowed routes for a given user_id using ACLCore models.

    - Reads user roles from ACLUserRole
    - Applies ACLRoleRoutePermission (deny > allow)
    - Returns a list of dicts with path/method/application and encoded method
    """
    cache_ttl = getattr(settings, "ACLCORE_CACHE_TTL_SECONDS", 3600)
    cache_key = _routes_cache_key(user_id, application)

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    app_obj: Optional[ACLApplication] = None
    if application:
        app_obj = ACLApplication.objects.filter(name=application).first()
        if app_obj is None:
            cache.set(cache_key, [], timeout=cache_ttl)
            return []

    roles_qs = ACLUserRole.objects.filter(user_id=user_id)
    if app_obj:
        roles_qs = roles_qs.filter(application=app_obj)

    role_ids = list(roles_qs.values_list("role_id", flat=True))
    if not role_ids:
        cache.set(cache_key, [], timeout=cache_ttl)
        return []

    route_qs = ACLRoute.objects.filter(is_active=True)
    if app_obj:
        route_qs = route_qs.filter(application=app_obj)

    # Deny > Allow
    denied_route_ids: Set[str] = set(
        ACLRoleRoutePermission.objects.filter(
            role_id__in=role_ids, is_allowed=False, route__in=route_qs
        ).values_list("route_id", flat=True)
    )
    allowed_perms = (
        ACLRoleRoutePermission.objects.filter(
            role_id__in=role_ids, is_allowed=True, route__in=route_qs
        )
        .select_related("route", "route__application")
        .order_by("route__path", "route__method")
    )

    routes: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for perm in allowed_perms:
        route = perm.route
        if route.pk in denied_route_ids or route.is_ignored:
            continue

        key = f"{route.application_id}:{route.method}:{route.path}"
        if key in seen:
            continue
        seen.add(key)

        routes.append(
            {
                "application": route.application.name if route.application else None,
                "path": route.path,
                "normalized_path": route.normalized_path,
                "method": route.method,
                "method_enc": _encode_method(route.method),
                "is_sensitive": route.is_sensitive,
            }
        )

    cache.set(cache_key, routes, timeout=cache_ttl)
    return routes


def get_routes_for_user(user_id: str, application: Optional[str] = None):
    return cache.get(_routes_cache_key(user_id, application))


def clear_routes_for_user(user_id: str, application: Optional[str] = None) -> None:
    cache.delete(_routes_cache_key(user_id, application))



