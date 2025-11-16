from __future__ import annotations

from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver

from aclcore.services import RouteRegistryService


class Command(BaseCommand):
    help = "Scan URLConf and register/update routes into ACL core"

    def add_arguments(self, parser):
        parser.add_argument("--application", type=str, default=None, help="Application name (optional)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without saving")

    def handle(self, *args, **options):
        application = options.get("application")
        dry_run = options.get("dry_run", False)
        registry = RouteRegistryService()

        def iter_patterns(urlpatterns, prefix=""):
            for p in urlpatterns:
                if isinstance(p, URLPattern):
                    yield prefix + str(p.pattern)
                elif isinstance(p, URLResolver):
                    yield from iter_patterns(p.url_patterns, prefix + str(p.pattern))

        count = 0
        for path in iter_patterns(get_resolver().url_patterns):
            # naive: assume GET allowed for registration baseline
            if not dry_run:
                registry.register(path=path, method="GET", application=application, is_sensitive=False, is_ignored=False)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Discovered {count} URL patterns{' (dry-run)' if dry_run else ''}"))


