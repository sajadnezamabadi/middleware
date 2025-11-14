from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response  # type: ignore
from rest_framework.views import APIView  # type: ignore
from rest_framework.viewsets import ModelViewSet  # type: ignore

from user.authentication_user import JWTAuthentication
from user.models import User
from user.serializers import StaffLoginSerializer, UserLoginSerializer, UserSerializer
from utils.acl.metrics import increment as metric_increment
from utils.acl.throttle import LoginAttemptLimiter


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


class UserLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "access": serializer.validated_data["access_token"],
                "user_id": serializer.validated_data["user"].id,
            },
            status=status.HTTP_200_OK,
        )


class StaffLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    login_limiter = LoginAttemptLimiter()

    def post(self, request, *args, **kwargs):
        username = str(request.data.get("username", "")).strip()
        metric_increment("admin_login_attempt_total")

        rate_result = self.login_limiter.allow(username)
        if not rate_result.allowed:
            metric_increment("admin_login_rate_limited_total")
            response = Response(
                {"detail": rate_result.error_message},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(rate_result.retry_after)
            return response

        serializer = StaffLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            metric_increment("admin_login_failure_total")
            raise

        self.login_limiter.reset(username)
        metric_increment("admin_login_success_total")
        metric_increment("admin_login_routes_generated_total", len(serializer.validated_data.get("routes", [])))

        return Response(
            {
                "access": serializer.validated_data["access_token"],
                "staff_id": serializer.validated_data["staff"].id,
                "expires_at": serializer.validated_data["expires_at"],
                "routes": serializer.validated_data["routes"],
            },
            status=status.HTTP_200_OK,
        )