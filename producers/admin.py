from django.contrib import admin
from .models import Productor, Departamento, Municipio


# --- Departamento & Municipio (Se mantienen igual para habilitar autocomplete) ---

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "created_at")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "get_departamento", "created_at")
    list_filter = ("id_departamento",)
    search_fields = ("nombre",)
    ordering = ("id_departamento__nombre", "nombre")
    autocomplete_fields = ("id_departamento",)

    def get_departamento(self, obj):
        return obj.id_departamento.nombre

    get_departamento.short_description = "Departamento"


# --- Productor Admin Corregido ---

@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    # 1. Mejoramos lo que se ve en la tabla principal
    list_display = (
        "nombre",
        "get_municipio",
        "get_departamento",
        "created_at",
        "updated_at"
    )

    # 2. Filtros laterales potentes (por región y fecha)
    list_filter = (
        "id_municipio__id_departamento",
        "id_municipio",
        "created_at"
    )

    # 3. Búsqueda expandida a los nombres de ubicación
    search_fields = (
        "nombre",
        "descripcion",
        "id_municipio__nombre",
        "id_municipio__id_departamento__nombre"
    )

    # 4. Implementación de Autocomplete (Basado en tu ejemplo de Producto)
    # Esto evita que el admin cargue miles de municipios en un select simple
    autocomplete_fields = ("id_municipio",)

    # 5. Optimización de base de datos (Evita N+1 queries)
    list_select_related = ("id_municipio", "id_municipio__id_departamento")

    ordering = ("nombre",)

    # --- Métodos para mostrar información jerárquica en la lista ---

    def get_municipio(self, obj):
        return obj.id_municipio.nombre if obj.id_municipio else "-"

    get_municipio.short_description = "Municipio"

    def get_departamento(self, obj):
        if obj.id_municipio and obj.id_municipio.id_departamento:
            return obj.id_municipio.id_departamento.nombre
        return "-"

    get_departamento.short_description = "Departamento"