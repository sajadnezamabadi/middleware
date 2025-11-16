from __future__ import annotations

from typing import Optional

from aclcore.models import ACLApplication, ACLRole, ACLUserRole, ACLRoute, ACLRoleRoutePermission


class RoleService:
    def _get_application(self, application: str | None) -> ACLApplication | None:
        if not application:
            return None
        app, _ = ACLApplication.objects.get_or_create(name=application)
        return app

    def ensure_role(self, code: str, application: str | None = None, is_super_role: bool = False) -> ACLRole:
        app = self._get_application(application)
        role, _ = ACLRole.objects.get_or_create(application=app, name=code, defaults={"is_super_role": is_super_role})
        if role.is_super_role != is_super_role:
            role.is_super_role = is_super_role
            role.save(update_fields=["is_super_role"])
        return role

    def assign_role(self, user_id: str, role_code: str, application: str | None = None) -> ACLUserRole:
        role = self.ensure_role(role_code, application=application)
        app = self._get_application(application)
        ur, _ = ACLUserRole.objects.get_or_create(user_id=user_id, application=app, role=role)
        return ur

    def revoke_role(self, user_id: str, role_code: str, application: str | None = None) -> int:
        app = self._get_application(application)
        return ACLUserRole.objects.filter(user_id=user_id, application=app, role__name=role_code).delete()[0]

    def allow_route_for_role(self, role_code: str, route: ACLRoute, allow: bool = True) -> ACLRoleRoutePermission:
        role = self.ensure_role(role_code, application=route.application.name if route.application else None)
        rp, _ = ACLRoleRoutePermission.objects.get_or_create(role=role, route=route, defaults={"is_allowed": allow})
        if rp.is_allowed != allow:
            rp.is_allowed = allow
            rp.save(update_fields=["is_allowed"])
        return rp


