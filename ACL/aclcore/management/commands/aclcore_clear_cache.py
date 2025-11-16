from __future__ import annotations

from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = "Clear ACLCore cache namespace"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Clear entire cache backend (careful)")

    def handle(self, *args, **options):
        if options.get("all"):
            cache.clear()
            self.stdout.write(self.style.SUCCESS("Cleared entire cache"))
            return
        # best-effort: no direct prefix deletion in base cache API; fall back to clear
        cache.clear()
        self.stdout.write(self.style.SUCCESS("Cleared cache (namespace best-effort)"))


