from __future__ import annotations

from typing import Callable, Optional

from django.conf import settings

from aclcore.models import ACLApplication, ACLRoute


def default_normalize_path(path: str) -> str:
    # Very simple normalizer; projects can override with ACLCORE_ROUTE_NORMALIZER
    # Removes trailing slashes except root and collapses multiple slashes
    p = path.strip()
    if p != "/" and p.endswith("/"):
        p = p[:-1]
    while "//" in p:
        p = p.replace("//", "/")
    return p or "/"


class RouteRegistryService:
    def __init__(self, normalizer: Optional[Callable[[str], str]] = None) -> None:
        self.normalize = normalizer or getattr(settings, "ACLCORE_ROUTE_NORMALIZER", default_normalize_path)

    def _get_application(self, name: str | None) -> ACLApplication | None:
        if not name:
            return None
        app, _ = ACLApplication.objects.get_or_create(name=name)
        return app

    def register(
        self,
        path: str,
        method: str,
        application: str | None = None,
        is_sensitive: bool = False,
        is_ignored: bool = False,
    ) -> ACLRoute:
        normalized_path = self.normalize(path)
        app = self._get_application(application)
        route, _ = ACLRoute.objects.get_or_create(
            application=app,
            path=path,
            method=method.upper(),
            defaults={
                "normalized_path": normalized_path,
                "is_sensitive": is_sensitive,
                "is_ignored": is_ignored,
                "is_active": True,
            },
        )
        if route.normalized_path != normalized_path or route.is_sensitive != is_sensitive or route.is_ignored != is_ignored:
            route.normalized_path = normalized_path
            route.is_sensitive = is_sensitive
            route.is_ignored = is_ignored
            route.save(update_fields=["normalized_path", "is_sensitive", "is_ignored"])
        return route


