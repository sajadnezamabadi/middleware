from __future__ import annotations

from typing import Iterable, Optional

from django.http import JsonResponse, HttpRequest
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

from aclcore.services import EvaluationService, default_normalize_path
from .signals import access_checked


def _get_setting(name: str, default):
    return getattr(settings, name, default)


class HttpAclMiddleware(MiddlewareMixin):
    """
    Lightweight ACL middleware:
    - Extract application name and user_id via configurable sources
    - Normalize path
    - Enforce allow/deny with cache
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.eval = EvaluationService()
        self.normalize = _get_setting("ACLCORE_ROUTE_NORMALIZER", default_normalize_path)
        self.default_app = _get_setting("ACLCORE_DEFAULT_APPLICATION", None)
        self.bypass_prefixes: Iterable[str] = _get_setting("ACLCORE_BYPASS_PREFIXES", ["/health", "/static", "/media"])
        self.user_id_header: str = _get_setting("ACLCORE_USER_ID_HEADER", "HTTP_X_USER_ID")
        self.app_header: str = _get_setting("ACLCORE_APPLICATION_HEADER", "HTTP_X_ACL_APP")
        self.log_sampling: float = float(_get_setting("ACLCORE_LOG_SAMPLING_RATE", 1.0))

    def process_request(self, request: HttpRequest):
        path = request.path or "/"
        for pfx in self.bypass_prefixes:
            if pfx and path.startswith(pfx):
                return None

        user_id = request.META.get(self.user_id_header)
        if not user_id:
            return JsonResponse({"detail": "missing user id"}, status=401)

        application = request.META.get(self.app_header) or self.default_app
        method = request.method.upper()

        result = self.eval.evaluate(user_id=user_id, method=method, path=path, application=application)

        # signal for observability (sampling internal)
        try:
            access_checked.send(
                sender=self.__class__,
                allowed=result.allowed,
                reason=result.reason,
                user_id=user_id,
                application=application,
                method=method,
                path=path,
                matched_route_id=result.matched_route_id,
                sampling_rate=self.log_sampling,
            )
        except Exception:
            pass

        if not result.allowed:
            return JsonResponse({"detail": "forbidden", "reason": result.reason}, status=403)
        return None


