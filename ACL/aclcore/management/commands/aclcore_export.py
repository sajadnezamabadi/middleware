from __future__ import annotations

import json
from django.core.management.base import BaseCommand

from aclcore.models import ACLApplication, ACLRole, ACLRoute, ACLRoleRoutePermission, ACLUserRole


class Command(BaseCommand):
    help = "Export ACL data (applications, routes, roles, mappings, user_roles) to JSON"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Output JSON file path")

    def handle(self, *args, **options):
        fp = options["file"]
        data = {
            "applications": list(ACLApplication.objects.values("id", "name", "description")),
            "routes": list(ACLRoute.objects.values("id", "application_id", "path", "normalized_path", "method", "is_active", "is_sensitive", "is_ignored")),
            "roles": list(ACLRole.objects.values("id", "application_id", "name", "is_super_role", "is_default", "description")),
            "role_route": list(ACLRoleRoutePermission.objects.values("id", "role_id", "route_id", "is_allowed")),
            "user_roles": list(ACLUserRole.objects.values("id", "user_id", "application_id", "role_id")),
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.stdout.write(self.style.SUCCESS(f"Exported ACL data to {fp}"))


