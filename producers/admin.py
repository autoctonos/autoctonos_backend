from django.contrib import admin
from .models import Productor

@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "origen","created_at", "updated_at")
    search_fields = ("nombre", "descripcion", "origen")
    ordering = ("nombre",)