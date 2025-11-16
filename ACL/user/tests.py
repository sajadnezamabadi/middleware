from django.test import TestCase, override_settings, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status

from user.models import Staff
from user.views import StaffLoginAPIView, UserLoginAPIView
from user.serializers import StaffLoginSerializer, UserLoginSerializer


def add_session_to_request(request):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request

class SessionOnlyLoginTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="user1", password="pass1234", is_active=True)
        self.staff = Staff.objects.create_user(username="admin1", password="pass1234", is_active=True)

    @override_settings(ADMIN_SESSION_ONLY_AUTH=True)
    def test_user_login_sets_session_and_no_token(self):
        view = UserLoginAPIView.as_view()
        request = self.factory.post("/", data={"username": "user1", "password": "pass1234"})
        request = add_session_to_request(request)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user_id", response.data)
        self.assertNotIn("access", response.data)
        self.assertEqual(request.session.get("user_id"), self.user.id)

    @override_settings(ADMIN_SESSION_ONLY_AUTH=True)
    def test_staff_login_sets_session_and_no_token(self):
        view = StaffLoginAPIView.as_view()
        request = self.factory.post("/", data={"username": "admin1", "password": "pass1234"})
        request = add_session_to_request(request)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("staff_id", response.data)
        self.assertNotIn("access", response.data)
        self.assertEqual(request.session.get("admin_staff_id"), self.staff.id)
