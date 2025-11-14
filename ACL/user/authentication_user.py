from datetime import datetime, timezone
from typing import Any, Dict

import jwt
from django.conf import settings
from rest_framework import exceptions  # type: ignore
from rest_framework.authentication import BaseAuthentication, get_authorization_header  # type: ignore

from user.models import User
from utils.messages import (
    ERROR_TOKEN_INVALID,
    ERROR_TOKEN_MISSING,
    ERROR_TOKEN_TYPE_INVALID,
    ERROR_USER_NOT_FOUND,
)

ALGORITHM = "HS256"


class JWTAuthentication(BaseAuthentication):
    """Authentication backend for customer access tokens."""

    def authenticate(self, request):
        raw_header = get_authorization_header(request).strip()
        if not raw_header:
            raise exceptions.AuthenticationFailed(ERROR_TOKEN_MISSING)

        token = raw_header.decode("utf-8")
        user_id = decode_access_token(token)

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed(ERROR_USER_NOT_FOUND) from exc

        return user, None


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": now + settings.JWT_ACCESS_TOKEN_LIFETIME,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm=ALGORITHM)
    
    
    
def decode_access_token(token: str) -> str:
    payload = _decode_token(token, settings.JWT_ACCESS_SECRET, expected_type="access")
    return payload["user_id"]


def _decode_token(token: str, secret: str, expected_type: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise exceptions.AuthenticationFailed(ERROR_TOKEN_INVALID) from exc
    except jwt.InvalidTokenError as exc:
        raise exceptions.AuthenticationFailed(ERROR_TOKEN_INVALID) from exc

    if payload.get("type") != expected_type:
        raise exceptions.AuthenticationFailed(ERROR_TOKEN_TYPE_INVALID)

    return payload