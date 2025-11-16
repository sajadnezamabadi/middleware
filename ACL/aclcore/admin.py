from django.contrib import admin
from .models import (
    ACLApplication,
    ACLRole,
    ACLPermission,
    ACLRoute,
    ACLRoleRoutePermission,
    ACLUserRole,
    ACLCacheEntry,
    ACLAccessLog,
)


@admin.register(ACLApplication)
class ACLApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(ACLRole)
class ACLRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "name", "is_super_role", "is_default")
    list_filter = ("application", "is_super_role", "is_default")
    search_fields = ("name",)


@admin.register(ACLPermission)
class ACLPermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "code")
    list_filter = ("application",)
    search_fields = ("code",)


@admin.register(ACLRoute)
class ACLRouteAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "method", "path", "is_active", "is_sensitive", "is_ignored")
    list_filter = ("application", "method", "is_active", "is_sensitive", "is_ignored")
    search_fields = ("path", "normalized_path")


@admin.register(ACLRoleRoutePermission)
class ACLRoleRoutePermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "role", "route", "is_allowed")
    list_filter = ("role__application", "is_allowed")
    search_fields = ("role__name", "route__path")


@admin.register(ACLUserRole)
class ACLUserRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "application", "role")
    list_filter = ("application", "role")
    search_fields = ("user_id",)


@admin.register(ACLCacheEntry)
class ACLCacheEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "route_hash", "is_allowed", "expires_at")
    list_filter = ("is_allowed",)
    search_fields = ("user_id", "route_hash")


@admin.register(ACLAccessLog)
class ACLAccessLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "route", "method", "allowed", "timestamp", "ip_address")
    list_filter = ("method", "allowed")
    search_fields = ("user_id", "ip_address")

# Register your models here.
