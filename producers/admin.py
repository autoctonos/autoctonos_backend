from django.contrib import admin
from .models import Productor


@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "get_municipio",
        "get_departamento",
        "created_at",
        "updated_at"
    )
    list_filter = (
        "id_municipio__id_departamento",
        "id_municipio",
        "created_at"
    )
    search_fields = (
        "nombre",
        "descripcion",
        "id_municipio__nombre",
        "id_municipio__id_departamento__nombre"
    )
    autocomplete_fields = ("id_municipio",)
    list_select_related = ("id_municipio", "id_municipio__id_departamento")
    ordering = ("nombre",)

    def get_municipio(self, obj):
        return obj.id_municipio.nombre if obj.id_municipio else "-"
    get_municipio.short_description = "Municipio"

    def get_departamento(self, obj):
        if obj.id_municipio and obj.id_municipio.id_departamento:
            return obj.id_municipio.id_departamento.nombre
        return "-"
    get_departamento.short_description = "Departamento"
