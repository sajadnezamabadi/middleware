class EndpointNotFound(Exception):
    """Raised when an incoming request cannot be mapped to a registered endpoint."""


class CacheUnavailable(Exception):
    """Raised when the Redis cache is not reachable."""

