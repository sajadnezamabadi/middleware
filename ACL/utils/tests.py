from django.test import TestCase, override_settings
from django.core.cache import cache

from aclcore.services import (
    increment as metric_increment,
    reset as metric_reset,
    snapshot,
    AdminRequestRateLimiter,
    LoginAttemptLimiter,
    build_routes_for_user,
    clear_routes_for_user,
    get_routes_for_user,
)
from utils.messages import ERROR_LOGIN_RATE_LIMIT_EXCEEDED, ERROR_RATE_LIMIT_EXCEEDED
from user.models import Staff
from aclcore.models import (
    ACLApplication,
    ACLRole,
    ACLRoleRoutePermission,
    ACLRoute,
    ACLUserRole,
)


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
        self.app = ACLApplication.objects.create(name="admin", description="Admin app")
        self.role = ACLRole.objects.create(application=self.app, name="admin-role")
        ACLUserRole.objects.create(user_id=str(self.staff.pk), application=self.app, role=self.role)
        self.route = ACLRoute.objects.create(
            application=self.app,
            path="/api/admin/example/",
            method="GET",
            normalized_path="/api/admin/example/",
            is_sensitive=False,
            is_ignored=False,
            is_active=True,
        )
        ACLRoleRoutePermission.objects.create(role=self.role, route=self.route, is_allowed=True)

    def tearDown(self) -> None:
        cache.clear()

    def test_routes_cached_and_retrieved(self):
        routes = build_routes_for_user(str(self.staff.pk), application=self.app.name)
        self.assertEqual(len(routes), 1)
        cached = get_routes_for_user(str(self.staff.pk), application=self.app.name)
        self.assertEqual(cached, routes)
        clear_routes_for_user(str(self.staff.pk), application=self.app.name)
        self.assertIsNone(get_routes_for_user(str(self.staff.pk), application=self.app.name))


# WebSocket auth tests removed.
# For WebSocket ACL testing, use aclcore.ws_middleware.WsAclMiddleware
# or aclcore.ws_middleware.SessionWSAuthMiddleware in your ASGI stack.
