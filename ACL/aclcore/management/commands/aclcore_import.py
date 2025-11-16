from __future__ import annotations

import json
from django.core.management.base import BaseCommand

from aclcore.models import ACLApplication, ACLRole, ACLRoute, ACLRoleRoutePermission, ACLUserRole


class Command(BaseCommand):
    help = "Import ACL data from JSON (applications, routes, roles, mappings, user_roles)"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Input JSON file path")

    def handle(self, *args, **options):
        fp = options["file"]
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        app_id_map = {}
        for a in data.get("applications", []):
            obj, _ = ACLApplication.objects.get_or_create(name=a["name"], defaults={"description": a.get("description")})
            app_id_map[a["id"]] = obj.id

        route_id_map = {}
        for r in data.get("routes", []):
            app = ACLApplication.objects.filter(id=app_id_map.get(r["application_id"])).first() if r.get("application_id") else None
            obj, _ = ACLRoute.objects.get_or_create(
                application=app,
                path=r["path"],
                method=r["method"],
                defaults={
                    "normalized_path": r.get("normalized_path") or r["path"],
                    "is_active": r.get("is_active", True),
                    "is_sensitive": r.get("is_sensitive", False),
                    "is_ignored": r.get("is_ignored", False),
                },
            )
            route_id_map[r["id"]] = obj.id

        role_id_map = {}
        for ro in data.get("roles", []):
            app = ACLApplication.objects.filter(id=app_id_map.get(ro["application_id"])).first() if ro.get("application_id") else None
            obj, _ = ACLRole.objects.get_or_create(
                application=app,
                name=ro["name"],
                defaults={
                    "is_super_role": ro.get("is_super_role", False),
                    "is_default": ro.get("is_default", False),
                    "description": ro.get("description"),
                },
            )
            role_id_map[ro["id"]] = obj.id

        for m in data.get("role_route", []):
            role_id = role_id_map.get(m["role_id"])
            route_id = route_id_map.get(m["route_id"])
            if role_id and route_id:
                ACLRoleRoutePermission.objects.get_or_create(role_id=role_id, route_id=route_id, defaults={"is_allowed": m.get("is_allowed", True)})

        for ur in data.get("user_roles", []):
            app_real_id = app_id_map.get(ur["application_id"]) if ur.get("application_id") else None
            ACLUserRole.objects.get_or_create(
                user_id=ur["user_id"],
                application_id=app_real_id,
                role_id=role_id_map.get(ur["role_id"]),
            )

        self.stdout.write(self.style.SUCCESS(f"Imported ACL data from {fp}"))


