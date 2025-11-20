"""
DEPRECATED: Thin compatibility layer for legacy `utils.acl` imports.

All core ACL functionality has moved to `aclcore.*`.
This module re-exports metrics/throttling for backwards compatibility only.

New code should import directly from `aclcore.services`:
    from aclcore.services import increment, LoginAttemptLimiter, ...
"""

# Re-export from aclcore for backwards compatibility
from aclcore.services import (
    increment,
    reset,
    snapshot,
    AdminRequestRateLimiter,
    LoginAttemptLimiter,
)

__all__ = [
    "increment",
    "reset",
    "snapshot",
    "AdminRequestRateLimiter",
    "LoginAttemptLimiter",
]

