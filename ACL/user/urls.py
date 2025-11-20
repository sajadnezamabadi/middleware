from django.urls import include, path
from rest_framework.routers import DefaultRouter  # type: ignore

from user.views import StaffLoginAPIView, UserLoginAPIView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    # CRUD for users
    path("", include(router.urls)),
    # Session/JWT login for normal users
    path("auth/login/", UserLoginAPIView.as_view(), name="user-login"),
    # Staff/admin login with ACL route generation
    path("admin/login/", StaffLoginAPIView.as_view(), name="staff-login"),
]


