from django.db import models
from django.conf import settings

from base.models import BaseIDModel, BaseModel, BaseActiveModel


class ACLApplication(BaseIDModel, BaseModel):
    name = models.CharField(max_length=150, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class ACLRole(BaseIDModel, BaseModel):
    application = models.ForeignKey(ACLApplication, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=150, db_index=True)
    is_super_role = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("application", "name")
        indexes = [models.Index(fields=["application", "name"])]

    def __str__(self):
        return f"{self.application}:{self.name}"


class ACLPermission(BaseIDModel, BaseModel):
    application = models.ForeignKey(ACLApplication, on_delete=models.CASCADE, related_name="permissions")
    code = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.code


class ACLRoute(BaseIDModel, BaseModel, BaseActiveModel):
    application = models.ForeignKey(ACLApplication, on_delete=models.CASCADE, related_name="routes")
    path = models.CharField(max_length=300, db_index=True)
    method = models.CharField(max_length=16, db_index=True)
    normalized_path = models.CharField(max_length=320, db_index=True, null=True, blank=True)
    is_sensitive = models.BooleanField(default=False)
    is_ignored = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["application", "method"]),
            models.Index(fields=["application", "normalized_path"]),
        ]
        unique_together = ("application", "path", "method")

    def __str__(self):
        return f"{self.application}:{self.method} {self.path}"


class ACLRoleRoutePermission(BaseIDModel, BaseModel):
    role = models.ForeignKey(ACLRole, on_delete=models.CASCADE, related_name="route_permissions")
    route = models.ForeignKey(ACLRoute, on_delete=models.CASCADE, related_name="role_permissions")
    is_allowed = models.BooleanField(default=True)
    conditions = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("role", "route")
        indexes = [models.Index(fields=["role", "route"])]


class ACLUserRole(BaseIDModel, BaseModel):
    user_id = models.CharField(max_length=100, db_index=True)
    application = models.ForeignKey(ACLApplication, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(ACLRole, on_delete=models.CASCADE, related_name="user_roles")

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "application"]),
        ]
        unique_together = ("user_id", "application", "role")


class ACLCacheEntry(BaseIDModel, BaseModel):
    user_id = models.CharField(max_length=100, db_index=True)
    route_hash = models.CharField(max_length=200, db_index=True)
    is_allowed = models.BooleanField(default=False)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "route_hash"]),
            models.Index(fields=["expires_at"]),
        ]


class ACLAccessLog(BaseIDModel, BaseModel):
    user_id = models.CharField(max_length=100, db_index=True)
    route = models.ForeignKey(ACLRoute, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs")
    method = models.CharField(max_length=16, db_index=True)
    allowed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "timestamp"]),
            models.Index(fields=["method", "timestamp"]),
        ]

# Create your models here.
