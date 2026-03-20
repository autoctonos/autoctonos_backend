from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class CustomUserAdmin(UserAdmin):

    list_display = ("username", "email", "first_name", "second_name", "is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {
            "fields": (
                "tipo_usuario",
                "nit",
                "second_name",
                "second_last_name",
                "address",
                "phone",
                "updated_at",
                "deleted_at"
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {
            "fields": (
                "tipo_usuario",
                "nit",
                "second_name",
                "second_last_name",
                "address",
                "phone"
            )
        }),
    )


    readonly_fields = ("updated_at", "deleted_at")

    def has_delete_permission(self, request, obj=None):

        if obj is not None:

            if obj.is_superuser:
                return False

        return super().has_delete_permission(request, obj)

admin.site.register(Usuario, CustomUserAdmin)