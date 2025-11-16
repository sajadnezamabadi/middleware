from __future__ import annotations

import random
from typing import List

from django.core.management.base import BaseCommand

from aclcore.models import (
    ACLApplication,
    ACLRoute,
    ACLRole,
    ACLRoleRoutePermission,
    ACLUserRole,
)
from aclcore.services import RouteRegistryService, RoleService


class Command(BaseCommand):
    help = "Seed ACLCore with fake data (applications, routes, roles, permissions, user roles). Requires 'Faker' package."

    def add_arguments(self, parser):
        parser.add_argument("--applications", type=int, default=1, help="Number of applications to create")
        parser.add_argument("--routes", type=int, default=15, help="Routes per application")
        parser.add_argument("--users", type=int, default=10, help="Number of fake users per application")
        parser.add_argument("--roles", type=int, default=2, help="Number of roles per application")
        parser.add_argument("--allow-rate", type=float, default=0.6, help="Probability of allow per (role,route) binding")
        parser.add_argument("--app-prefix", type=str, default="app", help="Application name prefix")

    def handle(self, *args, **options):
        try:
            from faker import Faker
        except Exception as exc:
            self.stderr.write(self.style.ERROR("Faker is not installed. Install with: pip install Faker"))
            raise SystemExit(1) from exc

        fake = Faker()
        Faker.seed(42)
        random.seed(42)

        num_apps = int(options["applications"])
        routes_per_app = int(options["routes"])
        users_per_app = int(options["users"])
        roles_per_app = max(1, int(options["roles"]))
        allow_rate = float(options["allow_rate"])
        app_prefix = str(options["app_prefix"]).strip() or "app"

        registry = RouteRegistryService()
        rolesvc = RoleService()

        created_apps: List[ACLApplication] = []
        for i in range(num_apps):
            app_name = f"{app_prefix}{i+1}"
            app, _ = ACLApplication.objects.get_or_create(name=app_name)
            created_apps.append(app)
            self.stdout.write(self.style.SUCCESS(f"[+] Application: {app_name}"))

            # create routes
            methods = ["GET", "POST", "PUT", "DELETE"]
            created_routes: List[ACLRoute] = []
            for _ in range(routes_per_app):
                path = f"/api/{app_name}/{fake.word().lower()}/"
                method = random.choice(methods)
                route = registry.register(path=path, method=method, application=app_name, is_sensitive=False, is_ignored=False)
                created_routes.append(route)
            self.stdout.write(f"    Routes created: {len(created_routes)}")

            # roles
            created_roles: List[ACLRole] = []
            for r in range(roles_per_app):
                role_code = f"{app_name.upper()}_ROLE_{r+1}"
                role = rolesvc.ensure_role(role_code, application=app_name, is_super_role=(r == 0 and roles_per_app == 1))
                created_roles.append(role)
            # always include ADMIN and VIEWER convenience roles
            created_roles.append(rolesvc.ensure_role("ADMIN", application=app_name, is_super_role=True))
            created_roles.append(rolesvc.ensure_role("VIEWER", application=app_name, is_super_role=False))
            self.stdout.write(f"    Roles created: {len(created_roles)}")

            # role-route bindings (random allow/deny)
            bindings = 0
            for role in created_roles:
                for route in created_routes:
                    allow = random.random() < allow_rate
                    ACLRoleRoutePermission.objects.update_or_create(
                        role=role,
                        route=route,
                        defaults={"is_allowed": allow},
                    )
                    bindings += 1
            self.stdout.write(f"    Role-route bindings: {bindings}")

            # assign roles to users
            assigned = 0
            for _ in range(users_per_app):
                user_id = f"user-{fake.uuid4()}"
                # each user gets 1-2 roles
                for role in random.sample(created_roles, k=min(len(created_roles), random.choice([1, 2]))):
                    ACLUserRole.objects.get_or_create(user_id=user_id, application=app, role=role)
                    assigned += 1
            self.stdout.write(f"    User-role assignments: {assigned}")

        self.stdout.write(self.style.SUCCESS("Seeding complete."))


