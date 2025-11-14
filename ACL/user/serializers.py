from django.utils import timezone
from rest_framework import serializers  # type: ignore

from user.authentication_user import create_access_token
from user.authentication_staff import create_access_token as create_staff_access_token
from user.models import Staff, User
from utils.acl import build_routes_for_token
from django.conf import settings
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
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({"username": ERROR_INVALID_CREDENTIALS}) from exc

        if not user.check_password(password):
            raise serializers.ValidationError({"password": ERROR_INVALID_CREDENTIALS})

        now = timezone.now()
        if user.first_login is None:
            user.first_login = now
        user.last_login = now
        user.save(update_fields=["first_login", "last_login"])

        attrs["user"] = user
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

        token = create_staff_access_token(str(staff.pk))
        expires_at = now + settings.JWT_ACCESS_TOKEN_LIFETIME
        routes = build_routes_for_token(staff, token)

        attrs["staff"] = staff
        attrs["access_token"] = token
        attrs["expires_at"] = expires_at
        attrs["routes"] = routes
        return attrs