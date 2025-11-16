from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings

from aclcore.models import ACLApplication, ACLRoute, ACLRoleRoutePermission, ACLUserRole
from .cache import CacheService
from .route_registry import default_normalize_path


@dataclass
class EvaluationResult:
    allowed: bool
    reason: str
    matched_route_id: Optional[str] = None


class EvaluationService:
    def __init__(self, cache: Optional[CacheService] = None) -> None:
        self.cache = cache or CacheService()
        self.normalize = getattr(settings, "ACLCORE_ROUTE_NORMALIZER", default_normalize_path)

    def _get_application(self, name: str | None) -> ACLApplication | None:
        if not name:
            return None
        app, _ = ACLApplication.objects.get_or_create(name=name)
        return app

    def evaluate(self, user_id: str, method: str, path: str, application: str | None = None) -> EvaluationResult:
        normalized = self.normalize(path)
        method_u = method.upper()

        cached = self.cache.get(application, user_id, method_u, normalized)
        if cached is not None:
            return EvaluationResult(allowed=bool(cached), reason="cache-hit", matched_route_id=None)

        app = self._get_application(application)
        try:
            route = ACLRoute.objects.get(application=app, normalized_path=normalized, method=method_u, is_active=True)
        except ACLRoute.DoesNotExist:
            self.cache.set(application, user_id, method_u, normalized, False)
            return EvaluationResult(allowed=False, reason="route-not-registered", matched_route_id=None)

        if route.is_ignored:
            self.cache.set(application, user_id, method_u, normalized, True)
            return EvaluationResult(allowed=True, reason="route-ignored", matched_route_id=str(route.pk))

        # Check user roles → role-route permissions
        roles = ACLUserRole.objects.filter(user_id=user_id, application=app).values_list("role_id", flat=True)
        if not roles:
            self.cache.set(application, user_id, method_u, normalized, False)
            return EvaluationResult(allowed=False, reason="no-roles", matched_route_id=str(route.pk))

        # deny > allow
        denies = ACLRoleRoutePermission.objects.filter(role_id__in=roles, route=route, is_allowed=False).exists()
        if denies:
            self.cache.set(application, user_id, method_u, normalized, False)
            return EvaluationResult(allowed=False, reason="explicit-deny", matched_route_id=str(route.pk))

        allows = ACLRoleRoutePermission.objects.filter(role_id__in=roles, route=route, is_allowed=True).exists()
        if allows:
            self.cache.set(application, user_id, method_u, normalized, True)
            return EvaluationResult(allowed=True, reason="explicit-allow", matched_route_id=str(route.pk))

        self.cache.set(application, user_id, method_u, normalized, False)
        return EvaluationResult(allowed=False, reason="no-matching-rule", matched_route_id=str(route.pk))


