from django.contrib import admin
from .models import Productor

@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "created_at", "updated_at")
    search_fields = ("nombre", "descripcion")
    ordering = ("nombre",)