from __future__ import annotations

import inspect
from typing import Iterable, List, Optional, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver

from utils.models import Endpoint
from utils.messages import SYNC_ENDPOINTS_DONE, SYNC_ENDPOINTS_DRY_RUN, SYNC_ENDPOINTS_HELP


class Command(BaseCommand):
    help = SYNC_ENDPOINTS_HELP

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=SYNC_ENDPOINTS_DRY_RUN,
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        admin_prefix = getattr(settings, "ADMIN_API_PREFIX", "/api/admin/")
        admin_prefix = admin_prefix.rstrip("/")

        resolver = get_resolver()
        discovered: Set[Tuple[str, str]] = set()

        patterns = list(self._iter_patterns(resolver))
        for full_path, callback in patterns:
            normalized_path = self._normalize_path(full_path)
            if not normalized_path.startswith(admin_prefix):
                continue

            methods = self._extract_methods(callback)
            service = callback.__module__
            action = getattr(callback, "__name__", "")

            if not methods:
                methods = ["GET"]

            for method in methods:
                key = (normalized_path, method)
                discovered.add(key)

                if dry_run:
                    self.stdout.write(f"[DRY-RUN] {method:<6} {normalized_path} ({service}.{action})")
                    continue

                Endpoint.objects.update_or_create(
                    path_pattern=normalized_path,
                    method=method,
                    defaults={
                        "service": service,
                        "action": action,
                        "is_active": True,
                    },
                )

        if not dry_run:
            self._deactivate_missing(admin_prefix, discovered)

        self.stdout.write(self.style.SUCCESS(SYNC_ENDPOINTS_DONE))

    def _iter_patterns(self, resolver: URLResolver, prefix: str = "") -> Iterable[Tuple[str, callable]]:
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                yield from self._iter_patterns(pattern, prefix + str(pattern.pattern))
            elif isinstance(pattern, URLPattern):
                yield prefix + str(pattern.pattern), pattern.callback

    def _normalize_path(self, raw_path: str) -> str:
        path = raw_path.replace("^", "").replace("$", "")
        if not path.startswith("/"):
            path = "/" + path
        return path

    def _extract_methods(self, callback) -> List[str]:
        methods: Set[str] = set()

        allowed = getattr(callback, "allowed_methods", None)
        if allowed:
            methods.update(m.upper() for m in allowed if m and m not in {"OPTIONS", "HEAD"})

        view_cls = getattr(callback, "cls", None)
        if view_cls and hasattr(view_cls, "http_method_names"):
            methods.update(
                m.upper()
                for m in getattr(view_cls, "http_method_names", [])
                if m and m not in {"options", "head"}
            )

        # DRF viewsets expose actions attribute with mapping method -> handler
        actions = getattr(callback, "actions", None)
        if isinstance(actions, dict):
            methods.update(m.upper() for m in actions.keys())

        if not methods:
            if inspect.isfunction(callback) or inspect.ismethod(callback):
                methods.add("GET")

        return sorted(methods)

    def _deactivate_missing(self, admin_prefix: str, discovered: Set[Tuple[str, str]]) -> None:
        active_endpoints = Endpoint.objects.filter(path_pattern__startswith=admin_prefix, is_active=True)
        for endpoint in active_endpoints:
            key = (endpoint.path_pattern, endpoint.method)
            if key not in discovered:
                endpoint.is_active = False
                endpoint.save(update_fields=["is_active"])

