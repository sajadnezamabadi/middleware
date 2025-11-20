from django.utils import timezone
from rest_framework import serializers  # type: ignore

from django.conf import settings
from django.contrib.auth import get_user_model
from user.authentication_user import create_access_token
from user.authentication_staff import create_access_token as create_staff_access_token
from user.models import Staff, User
from aclcore.services import build_routes_for_user
from utils.messages import ERROR_INVALID_CREDENTIALS, ERROR_PASSWORD_REQUIRED


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "gender",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": ERROR_PASSWORD_REQUIRED})

        instance = User(**validated_data)
        instance.set_password(password)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(username=username, is_active=True)
        except UserModel.DoesNotExist as exc:
            raise serializers.ValidationError({"username": ERROR_INVALID_CREDENTIALS}) from exc

        if not user.check_password(password):
            raise serializers.ValidationError({"password": ERROR_INVALID_CREDENTIALS})

        now = timezone.now()
        update_fields = []
        if hasattr(user, "first_login"):
            if getattr(user, "first_login") is None:
                setattr(user, "first_login", now)
                update_fields.append("first_login")
        if hasattr(user, "last_login"):
            setattr(user, "last_login", now)
            update_fields.append("last_login")
        if update_fields:
            user.save(update_fields=update_fields)

        attrs["user"] = user
        if not getattr(settings, "ADMIN_SESSION_ONLY_AUTH", True):
            attrs["access_token"] = create_access_token(str(user.pk))
        return attrs


class StaffLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        try:
            staff = Staff.objects.get(username=username, is_active=True)
        except Staff.DoesNotExist as exc:
            raise serializers.ValidationError({"username": ERROR_INVALID_CREDENTIALS}) from exc

        if not staff.check_password(password):
            raise serializers.ValidationError({"password": ERROR_INVALID_CREDENTIALS})

        now = timezone.now()
        staff.last_login = now
        staff.save(update_fields=["last_login"])

        routes = build_routes_for_user(str(staff.pk))

        attrs["staff"] = staff
        attrs["routes"] = routes
        if not getattr(settings, "ADMIN_SESSION_ONLY_AUTH", True):
            token = create_staff_access_token(str(staff.pk))
            expires_at = now + settings.JWT_ACCESS_TOKEN_LIFETIME
            attrs["access_token"] = token
            attrs["expires_at"] = expires_at
        return attrs