from __future__ import annotations

from typing import Optional, Dict, Any
from urllib.parse import parse_qs

from aclcore.services import EvaluationService, default_normalize_path


class WsAclMiddleware:
    """
    ASGI middleware for WebSocket ACL enforcement.
    - Reads user_id from headers (x-user-id) or query (?user_id=...)
    - Uses path and method='WS' for evaluation
    - Optional application from header (x-acl-app)
    """

    def __init__(self, app):
        self.app = app
        self.eval = EvaluationService()

    async def __call__(self, scope: Dict[str, Any], receive, send):
        if scope["type"] != "websocket":
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        query_params = parse_qs(scope.get("query_string", b"").decode())

        user_id = headers.get("x-user-id") or (query_params.get("user_id", [None])[-1])
        application = headers.get("x-acl-app") or None

        if not user_id:
            await self._deny(send, code=4401, reason="missing user id")
            return

        path = scope.get("path") or "/"
        result = self.eval.evaluate(user_id=user_id, method="WS", path=path, application=application)
        if not result.allowed:
            await self._deny(send, code=4403, reason=result.reason)
            return

        return await self.app(scope, receive, send)

    @staticmethod
    async def _deny(send, code: int, reason: str):
        await send({"type": "websocket.close", "code": code, "reason": reason})

from __future__ import annotations

from typing import Optional, Union, Callable, Awaitable
from urllib.parse import parse_qs

from django.conf import settings
from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser

from aclcore.models import ACLUserRole, ACLApplication


class SessionWSAuthMiddleware:
    """
    Minimal WS middleware (framework-agnostic):
    - Accepts ?user_id=<id>[&app=<name>]
    - Resolves to a pseudo user object with only .is_authenticated and .id
    - Does not perform ACL; only identification for upstream usage
    """

    def __init__(self, inner: Callable[..., Awaitable]):
        self.inner = inner
        self.default_app = getattr(settings, "ACLCORE_DEFAULT_APPLICATION", None)

    async def __call__(self, scope, receive, send):
        user = AnonymousUser()
        try:
            query_params = parse_qs(scope.get("query_string", b"").decode())
            user_id = (query_params.get("user_id") or [None])[-1]
            app_name = (query_params.get("app") or [self.default_app])[-1]

            if user_id:
                # no DB lookup required; attach a lightweight object
                # ensure user has at least one role if application is specified (optional)
                if await _has_any_role(user_id, app_name):
                    user = type("WsUser", (), {"is_authenticated": True, "id": user_id})()
        except Exception:
            user = AnonymousUser()

        scope["user"] = user
        return await self.inner(scope, receive, send)


@sync_to_async
def _has_any_role(user_id: str, app_name: Optional[str]) -> bool:
    if app_name:
        app = ACLApplication.objects.filter(name=app_name).first()
        return ACLUserRole.objects.filter(user_id=user_id, application=app).exists()
    return ACLUserRole.objects.filter(user_id=user_id, application__isnull=True).exists()


