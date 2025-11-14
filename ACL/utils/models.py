from django.conf import settings
from django.db import models

from base.models import BaseActiveModel, BaseIDModel, BaseModel
from user.choices import RoleChoices


class Endpoint(BaseIDModel, BaseModel, BaseActiveModel):
    service = models.CharField(max_length=100, db_index=True)
    path_pattern = models.CharField(max_length=300, unique=True, db_index=True)
    method = models.CharField(max_length=16, db_index=True)
    action = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["service", "method"]),
        ]
        verbose_name = "Endpoint"
        verbose_name_plural = "Endpoints"

    def __str__(self):
        return f"{self.service}:{self.method} {self.path_pattern}"


class MethodEncoding(BaseModel):
    method = models.CharField(max_length=16, unique=True)
    encoded = models.CharField(max_length=16)

    class Meta:
        verbose_name = "Method Encoding"
        verbose_name_plural = "Method Encodings"

    def __str__(self):
        return f"{self.method}->{self.encoded}"


class ACLRule(BaseIDModel, BaseModel):
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name="acl_rules")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acl_rules",
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=50,
        choices=RoleChoices.choices,
        null=True,
        blank=True,
        db_index=True,
    )
    team = models.ForeignKey(
        "user.Team",
        on_delete=models.CASCADE,
        related_name="acl_rules",
        null=True,
        blank=True,
    )
    allow = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False)
                    | models.Q(role__isnull=False)
                    | models.Q(team__isnull=False)
                ),
                name="aclrule_subject_not_null",
            ),
        ]
        ordering = ["-priority", "id"]
        verbose_name = "ACL Rule"
        verbose_name_plural = "ACL Rules"

    def __str__(self):
        target = self.user or self.role or (self.team and self.team.name_en) or "unknown"
        return f"{self.endpoint} -> {target}"


