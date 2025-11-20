from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Core API entrypoint for this ACL backend
    path("api/", include("user.urls")),
]
