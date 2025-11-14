from django.db import models
from django.utils.translation import gettext_lazy as _




class GenderChoices(models.TextChoices):
    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")



class RoleChoices(models.TextChoices):
    SUPER_USER = "SuperUser", _("Super admin")
    ADMIN = "Admin", _("Admin")
    API_KEY = "ApiKey", _("API key")


class TeamChoices(models.TextChoices):
    DEFAULT = "default", _("Default")
    DEVOPS = "devops", _("DevOps")
    DEVELOPER = "developer", _("Developer")
    MANAGERS = "managers", _("Managers")
    GENERAL_MANAGER = "general_manager", _("General manager")
    GENERAL_DIRECTOR = "general_director", _("General director")
    GENERAL_SECRETARY = "general_secretary", _("General secretary")