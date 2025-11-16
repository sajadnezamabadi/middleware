from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator
from django.db import models

from base.models import BaseActiveModel, BaseIDModel, BaseModel
from user.choices import GenderChoices, RoleChoices, TeamChoices


class Acl(BaseIDModel, BaseModel, BaseActiveModel):
    route_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    route_method = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True, verbose_name="Description", db_index=True)
    is_active = models.BooleanField(default=True, verbose_name="Active", db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")


class Team(BaseIDModel, BaseModel, BaseActiveModel):
    name_en = models.CharField(
        max_length=50, choices=TeamChoices.choices, null=True, blank=True, verbose_name="english name", db_index=True
    )

    acl = GenericRelation(Acl, related_query_name="teams", related_name="teams")


class Staff(BaseIDModel, BaseModel, BaseActiveModel):
    class StaffManager(models.Manager):
        def create_user(self, username: str, password: str | None = None, **extra_fields):
            staff = self.model(username=username, **extra_fields)
            if password:
                staff.set_password(password)
            staff.save(using=self._db)
            return staff

    username = models.CharField(max_length=50, unique=True, verbose_name="Username", db_index=True)
    password = models.CharField(max_length=128, verbose_name="Password")
    first_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="First name", db_index=True)
    last_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="Last name", db_index=True)
    gender = models.CharField(null=True, blank=True, choices=GenderChoices.choices, verbose_name="Gender", db_index=True)
    phone_number = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        validators=[RegexValidator(regex="^0[0-9]{10}$", message="Phone number format is invalid.")],
    )
    email = models.EmailField(null=True, blank=True, verbose_name="Email", db_index=True)
    team = models.ManyToManyField("Team", verbose_name="Team", db_index=True)
    role = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Role", db_index=True, choices=RoleChoices.choices
    )
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Last login")
    acl = GenericRelation(Acl, related_query_name="staffs", related_name="staffs")

    objects = StaffManager()

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)


class User(BaseIDModel, BaseModel, BaseActiveModel):
    username = models.CharField(max_length=50, unique=True, verbose_name="Username", db_index=True)
    password = models.CharField(max_length=128, verbose_name="Password")
    email = models.EmailField(null=True, blank=True, verbose_name="Email", db_index=True)
    phone_number = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        validators=[RegexValidator(regex="^0[0-9]{10}$", message="Phone number format is invalid.")],
    )
    first_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="First name", db_index=True)
    last_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="Last name", db_index=True)
    gender = models.CharField(null=True, blank=True, choices=GenderChoices.choices, verbose_name="Gender", db_index=True)

    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Last login")
    first_login = models.DateTimeField(null=True, blank=True, verbose_name="First login")
    national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="National code", db_index=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name="Birth date")
    postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="Postal code", db_index=True)
    bank_account = models.CharField(max_length=50, null=True, blank=True, verbose_name="Bank account", db_index=True)
    extra_info = models.JSONField(null=True, blank=True, verbose_name="Extra information")

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def full_name(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def __str__(self) -> str:
        return self.full_name() or self.username

    @property
    def is_authenticated(self) -> bool:
        return True
