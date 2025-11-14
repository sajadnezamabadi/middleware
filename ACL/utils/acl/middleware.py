from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from user.authentication_staff import decode_access_token
from user.models import Staff
from user.choices import RoleChoices
from utils.acl.builder import build_routes_for_token, get_routes_for_token
from utils.acl.engine import ACLDecisionEngine
from utils.acl.exceptions import EndpointNotFound
from utils.acl.metrics import increment as metric_increment
from utils.acl.resolver import EndpointResolver
from utils.acl.throttle import AdminRequestRateLimiter
from utils.messages import (
    ERROR_ACCESS_FORBIDDEN,
    ERROR_ENDPOINT_NOT_FOUND,
    ERROR_INTERNAL_SERVER,
    ERROR_METHOD_NOT_ALLOWED,
    ERROR_RATE_LIMIT_EXCEEDED,
    ERROR_TOKEN_INVALID,
    ERROR_TOKEN_MISSING,
)
from utils.models import MethodEncoding

logger = logging.getLogger(__name__)


class AdminACLMiddleware:
    """
    Base middleware that guards admin-side routes (default prefix: /api/admin/).
    Tokens are expected in the Authorization header without the Bearer prefix.
    Super users bypass all checks; other roles must pass ACL and method validation.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = getattr(settings, "ADMIN_API_PREFIX", "/api/admin/")
        self.resolver = EndpointResolver()
        self.engine = ACLDecisionEngine()
        self.rate_limiter = AdminRequestRateLimiter()

    def __call__(self, request):
        path = request.path_info or ""
        if not path.startswith(self.admin_prefix):
            return self.get_response(request)

        staff_or_response = self._authenticate_staff(request)
        if isinstance(staff_or_response, JsonResponse):
            return staff_or_response

        staff = staff_or_response["staff"]
        token = staff_or_response["token"]
        request.staff = staff  # type: ignore[attr-defined]
        metric_increment("admin_auth_success_total")

        rate_result = self.rate_limiter.allow(token)
        if not rate_result.allowed:
            metric_increment("admin_rate_limited_total")
            logger.warning(
                "Admin request rate limited",
                extra={
                    "staff_id": str(staff.pk),
                    "token": token[:8],
                    "retry_after": rate_result.retry_after,
                    "path": request.path_info,
                },
            )
            response = JsonResponse(
                {"detail": rate_result.error_message or ERROR_RATE_LIMIT_EXCEEDED},
                status=429,
            )
            response["Retry-After"] = str(rate_result.retry_after)
            return response

        routes = get_routes_for_token(token)
        if routes is None:
            routes = build_routes_for_token(staff, token)

        if staff.role == RoleChoices.SUPER_USER:
            logger.info(
                "Admin request allowed for super user",
                extra={
                    "staff_id": str(staff.pk),
                    "path": request.path_info,
                    "method": request.method,
                },
            )
            metric_increment("admin_acl_allowed_total")
            request.acl_routes = routes  # type: ignore[attr-defined]
            request.access_token = token  # type: ignore[attr-defined]
            return self.get_response(request)

        try:
            endpoint_payload = self.resolver.resolve(request)
        except EndpointNotFound:
            metric_increment("admin_endpoint_not_found_total")
            return JsonResponse({"detail": ERROR_ENDPOINT_NOT_FOUND}, status=404)
        except Exception as exc:
            logger.exception(
                "Failed to resolve endpoint for admin ACL",
                exc_info=exc,
                extra={"staff_id": str(staff.pk), "path": request.path_info},
            )
            metric_increment("admin_acl_internal_error_total")
            return JsonResponse({"detail": ERROR_INTERNAL_SERVER}, status=500)

        if not self.engine.is_allowed(staff, endpoint_payload):
            metric_increment("admin_acl_denied_total")
            logger.warning(
                "Admin ACL denied",
                extra={
                    "staff_id": str(staff.pk),
                    "endpoint_id": endpoint_payload.get("id"),
                    "method": request.method,
                    "path": request.path_info,
                },
            )
            return JsonResponse({"detail": ERROR_ACCESS_FORBIDDEN}, status=403)

        if not self._is_method_allowed(routes, endpoint_payload, request.method.upper()):
            metric_increment("admin_method_denied_total")
            logger.warning(
                "Admin method denied",
                extra={
                    "staff_id": str(staff.pk),
                    "endpoint_id": endpoint_payload.get("id"),
                    "method": request.method,
                    "path": request.path_info,
                },
            )
            return JsonResponse({"detail": ERROR_METHOD_NOT_ALLOWED}, status=403)

        metric_increment("admin_acl_allowed_total")
        logger.info(
            "Admin ACL allowed",
            extra={
                "staff_id": str(staff.pk),
                "endpoint_id": endpoint_payload.get("id"),
                "method": request.method,
                "path": request.path_info,
            },
        )
        request.endpoint_payload = endpoint_payload  # type: ignore[attr-defined]
        request.access_token = token  # type: ignore[attr-defined]
        request.acl_routes = routes  # type: ignore[attr-defined]
        return self.get_response(request)

    def _authenticate_staff(self, request) -> dict | JsonResponse:
        raw_token = self._extract_token(request)
        if not raw_token:
            metric_increment("admin_auth_failure_total")
            return JsonResponse({"detail": ERROR_TOKEN_MISSING}, status=401)

        try:
            staff_id = decode_access_token(raw_token)
        except Exception:
            metric_increment("admin_auth_failure_total")
            return JsonResponse({"detail": ERROR_TOKEN_INVALID}, status=401)

        try:
            staff = Staff.objects.get(pk=staff_id, is_active=True)
        except Staff.DoesNotExist:
            metric_increment("admin_auth_failure_total")
            return JsonResponse({"detail": ERROR_ACCESS_FORBIDDEN}, status=401)

        return {"staff": staff, "token": raw_token}

    def _extract_token(self, request) -> Optional[str]:
        header = request.META.get("HTTP_AUTHORIZATION", "").strip()
        if header:
            return header
        return request.headers.get("Authorization")

    def _is_method_allowed(self, routes: list[dict[str, str]], endpoint_payload: dict, method: str) -> bool:
        if not routes:
            return True
        encoded = MethodEncoding.objects.filter(method=method).first()
        encoded_value = encoded.encoded if encoded else ""
        if not encoded_value:
            return True

        endpoint_id = str(endpoint_payload["id"])
        for route in routes:
            if route.get("endpoint_id") == endpoint_id:
                stored_methods = route.get("encoded_method", "")
                return encoded_value in stored_methods
        return True

