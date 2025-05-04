from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import User


class DeletedFilter(admin.SimpleListFilter):
    title = "Usuarios Eliminados"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return [
            ("deleted", "Eliminados"),
            ("active", "Activos"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = [
        "email",
        "username",
        "is_staff",
        "is_active",
        "created_at",
        "deleted_at",
    ]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("username",)}),
        (
            "Permisos",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]
    search_fields = ("email", "username")
    ordering = ("-created_at",)
    list_filter = (DeletedFilter, "is_active")
    actions = ["undelete_selected", "soft_delete_users"]

    def get_queryset(self, request):
        return User.all_objects.all()

    def soft_delete_users(self, request, queryset):
        queryset.update(deleted_at=timezone.now())
        self.message_user(
            request, "Los usuarios seleccionados fueron eliminados (soft delete).")

    soft_delete_users.short_description = "Eliminar usuarios (Soft Delete)"

    def undelete_selected(self, request, queryset):
        queryset.update(deleted_at=None)
        self.message_user(
            request, "Los usuarios seleccionados fueron restaurados exitosamente.")

    undelete_selected.short_description = "Restaurar usuarios seleccionados"


admin.site.register(User, CustomUserAdmin)
