from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario  

class CustomUserAdmin(UserAdmin):

    list_display = ("username", "email", "phone", "is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("address", "phone", "updated_at", "deleted_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("address", "phone")}),
    )

admin.site.register(Usuario, CustomUserAdmin)
