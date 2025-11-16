from django.test import TestCase, override_settings
from django.core.cache import cache
from django.test import override_settings
from asgiref.sync import async_to_sync

from utils.acl.metrics import increment as metric_increment, reset as metric_reset, snapshot
from utils.acl.throttle import AdminRequestRateLimiter, LoginAttemptLimiter
from utils.acl import build_routes_for_staff, get_routes_for_staff, clear_routes_for_staff
from utils.messages import ERROR_LOGIN_RATE_LIMIT_EXCEEDED, ERROR_RATE_LIMIT_EXCEEDED
from user.models import Staff
from utils.models import Endpoint, MethodEncoding, ACLRule
from utils.websocket_auth import SessionAuthMiddleware, cache_get_ws_session


class LoginAttemptLimiterTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        metric_reset("admin_login_attempt_total")

    @override_settings(ADMIN_LOGIN_ATTEMPT_LIMIT=2, ADMIN_LOGIN_BLOCK_SECONDS=10)
    def test_login_attempts_block_after_limit(self):
        limiter = LoginAttemptLimiter()
        result1 = limiter.allow("admin")
        self.assertTrue(result1.allowed)
        result2 = limiter.allow("admin")
        self.assertTrue(result2.allowed)
        result3 = limiter.allow("admin")
        self.assertFalse(result3.allowed)
        self.assertEqual(result3.error_message, ERROR_LOGIN_RATE_LIMIT_EXCEEDED)

        limiter.reset("admin")
        result4 = limiter.allow("admin")
        self.assertTrue(result4.allowed)


class AdminRequestRateLimiterTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    @override_settings(ADMIN_RATE_LIMIT_REQUESTS=2, ADMIN_RATE_LIMIT_WINDOW_SECONDS=30)
    def test_request_rate_limiter_blocks_after_threshold(self):
        limiter = AdminRequestRateLimiter()
        identifier = "staff-123"
        first = limiter.allow(identifier)
        self.assertTrue(first.allowed)
        second = limiter.allow(identifier)
        self.assertTrue(second.allowed)
        third = limiter.allow(identifier)
        self.assertFalse(third.allowed)
        self.assertEqual(third.error_message, ERROR_RATE_LIMIT_EXCEEDED)


class MetricsTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    def test_metrics_increment_and_snapshot(self):
        metric_reset("example_metric")
        metric_increment("example_metric")
        metric_increment("example_metric", amount=4)
        data = snapshot(["example_metric"])
        self.assertEqual(data["example_metric"], 5)


class RouteBuilderTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.staff = Staff.objects.create(username="admin", password="secret")
        self.endpoint = Endpoint.objects.create(
            service="api.admin",
            path_pattern="/api/admin/example/",
            method="GET",
            action="list-things",
            is_active=True,
        )
        MethodEncoding.objects.create(method="GET", encoded="D")
        ACLRule.objects.create(endpoint=self.endpoint, user=self.staff, allow=True, priority=10)

    def tearDown(self) -> None:
        cache.clear()

    def test_routes_cached_and_retrieved(self):
        routes = build_routes_for_staff(self.staff)
        self.assertEqual(len(routes), 1)
        cached = get_routes_for_staff(str(self.staff.pk))
        self.assertEqual(cached, routes)
        clear_routes_for_staff(str(self.staff.pk))
        self.assertIsNone(get_routes_for_staff(str(self.staff.pk)))


class WebsocketAuthTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.staff = Staff.objects.create(username="wsadmin", password="secret", is_active=True)

    @override_settings()
    def test_ws_session_auth_resolves_staff(self):
        # Seed cache
        cache.set(f"ws_session:testkey", str(self.staff.pk), timeout=60)

        captured_user = {}

        async def inner(scope, receive, send):
            captured_user["user"] = scope.get("user")

        middleware = SessionAuthMiddleware(inner)
        scope = {"query_string": b"session=testkey", "headers": []}
        async_to_sync(middleware)(scope, None, None)

        self.assertIsNotNone(captured_user.get("user"))
        self.assertEqual(getattr(captured_user["user"], "pk", None), self.staff.pk)
