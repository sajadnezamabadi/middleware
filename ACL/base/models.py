import re
import uuid
from django.db import models
from django.db.models.manager import Manager



class BaseManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_trashed(self):
        return super().get_queryset()


class BaseDeletedModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    objects = BaseManager()
    all_objects = Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def restore(self, *args, **kwargs):
        self.is_deleted = False
        self.save()

    def force_delete(self, *args, **kwargs):
        return super().delete()


class BaseIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class BaseAutoFieldModel(models.Model):
    id = models.AutoField(primary_key=True, auto_created=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseActiveModel(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


        