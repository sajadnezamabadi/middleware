from __future__ import annotations

import logging
from typing import Union, Optional
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async as database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from user.models import User, Staff


logger = logging.getLogger(__name__)


def cache_get_ws_session(session_key: str) -> Optional[str]:
    """
    Fetch user/staff identifier associated with a websocket session key from cache.
    Does not store any tokens; value should be a user or staff id string.
    """
    try:
        value = cache.get(f"ws_session:{session_key}")
        if value is None:
            return None
        return str(value)
    except Exception:
        return None


class SessionAuthMiddleware:
    """
    Channels WebSocket auth middleware (session-key based).
    - Accepts ?session=<key> in query string.
    - Resolves to User or Staff via cache mapping.
    - Does NOT accept or store any access tokens.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        user = None
        try:
            query_params = parse_qs(scope.get("query_string", b"").decode())
            session_values = query_params.get("session")
            session_key = session_values[-1] if session_values else None

            if session_key:
                identifier = cache_get_ws_session(session_key)
                if identifier:
                    user = await self._get_user_or_staff(identifier)
        except Exception:
            logger.exception("websocket auth: unexpected error during session authentication")
            user = None

        scope["user"] = user or AnonymousUser()
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _get_user_or_staff(self, identifier: str) -> Union[User, Staff, None]:
        """
        Resolve identifier to User or Staff. Prefer Staff if numeric, else User.
        """
        # Try Staff by primary key (supports UUID or int)
        try:
            return Staff.objects.get(pk=identifier, is_active=True)
        except Staff.DoesNotExist:
            pass

        # Fallback: User by string PK
        try:
            return User.objects.get(pk=identifier, is_active=True)
        except User.DoesNotExist:
            return None


def SessionAuthMiddlewareStack(app):
    return SessionAuthMiddleware(app)


