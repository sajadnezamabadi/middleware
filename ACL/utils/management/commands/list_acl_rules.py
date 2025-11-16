from __future__ import annotations

from django.core.management.base import BaseCommand
from aclcore.models import ACLApplication, ACLRoute, ACLRole, ACLRoleRoutePermission, ACLUserRole


class Command(BaseCommand):
    help = "List ACLCore role-route permissions grouped by route, with optional filters."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Filter by route path (substring match).",
        )
        parser.add_argument(
            "--role",
            type=str,
            help="Filter by role code (exact match).",
        )
        parser.add_argument(
            "--application",
            type=str,
            help="Filter by application name (exact match).",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Filter by user_id (lists roles assigned; does not filter permissions).",
        )

    def handle(self, *args, **options):
        application_name = options.get("application")
        path_filter = options.get("path")
        role_filter = options.get("role")
        user_filter = options.get("user")

        app = None
        if application_name:
            app = ACLApplication.objects.filter(name=application_name).first()
            if app is None:
                self.stdout.write(self.style.WARNING(f"Application '{application_name}' not found"))
                return

        routes = ACLRoute.objects.all().order_by("path", "method")
        if app:
            routes = routes.filter(application=app)
        if path_filter:
            routes = routes.filter(path__icontains=path_filter)

        if not routes.exists():
            self.stdout.write(self.style.WARNING("No routes found with the given filters."))
            return

        # Optionally show user roles
        if user_filter:
            qs = ACLUserRole.objects.filter(user_id=user_filter)
            if app:
                qs = qs.filter(application=app)
            roles = list(qs.select_related("role").values_list("role__name", flat=True))
            self.stdout.write(self.style.NOTICE(f"user_id={user_filter} roles={roles or '[]'}"))

        for route in routes:
            self.stdout.write("")
            app_label = route.application.name if route.application else "default"
            self.stdout.write(self.style.NOTICE(f"[{app_label}] {route.method} {route.path} (ignored={route.is_ignored}, active={route.is_active})"))

            perms = ACLRoleRoutePermission.objects.filter(route=route).select_related("role").order_by("role__name")
            if role_filter:
                perms = perms.filter(role__name=role_filter)

            if not perms.exists():
                self.stdout.write("  - (no role bindings)")
                continue

            for p in perms:
                status = "ALLOW" if p.is_allowed else "DENY"
                self.stdout.write(f"  - {status:<5} role={p.role.name}")

