from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario  # Importa tu modelo de usuario personalizado

class CustomUserAdmin(UserAdmin):
    # Define qué campos se mostrarán en la lista de usuarios
    list_display = ("username", "email", "phone", "is_staff", "is_active")
    # Define los campos editables en el admin
    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("address", "phone", "updated_at", "deleted_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("address", "phone")}),
    )

# Registra el modelo en el admin
admin.site.register(Usuario, CustomUserAdmin)
