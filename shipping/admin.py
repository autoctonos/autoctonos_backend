from django.contrib import admin

from .models import CoberturaMunicipio, ConfiguracionEmpaque, PromocionEnvio, Trayecto


@admin.register(Trayecto)
class TrayectoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "jerarquia",
        "valor_kilo_inicial",
        "valor_kilo_adicional",
        "sobreflete_minimo",
        "porcentaje_sobreflete",
        "dias_entrega_min",
        "dias_entrega_max",
        "activo",
        "updated_at",
    )
    list_editable = (
        "valor_kilo_inicial",
        "valor_kilo_adicional",
        "sobreflete_minimo",
        "porcentaje_sobreflete",
        "dias_entrega_min",
        "dias_entrega_max",
        "activo",
    )
    search_fields = ("nombre", "codigo")
    ordering = ("jerarquia",)


class TieneOrigenFilter(admin.SimpleListFilter):
    title = "rol en la red"
    parameter_name = "rol"

    def lookups(self, request, model_admin):
        return (
            ("origen", "Sirve como origen"),
            ("solo_destino", "Sólo destino"),
        )

    def queryset(self, request, queryset):
        if self.value() == "origen":
            return queryset.filter(trayecto_origen__isnull=False)
        if self.value() == "solo_destino":
            return queryset.filter(trayecto_origen__isnull=True)
        return queryset


@admin.register(CoberturaMunicipio)
class CoberturaMunicipioAdmin(admin.ModelAdmin):
    list_display = (
        "municipio",
        "departamento",
        "provincia",
        "trayecto_origen",
        "trayecto_destino",
        "distancia_km_tunja",
        "activo",
    )
    list_editable = ("trayecto_origen", "trayecto_destino", "activo")
    list_filter = ("activo", "trayecto_origen", "trayecto_destino", TieneOrigenFilter,
                   "municipio__id_departamento")
    search_fields = ("municipio__nombre", "municipio__id_departamento__nombre", "provincia")
    autocomplete_fields = ("municipio",)
    list_select_related = ("municipio", "municipio__id_departamento", "trayecto_origen", "trayecto_destino")

    def departamento(self, obj):
        return obj.municipio.id_departamento.nombre
    departamento.short_description = "Departamento"
    departamento.admin_order_field = "municipio__id_departamento__nombre"


@admin.register(ConfiguracionEmpaque)
class ConfiguracionEmpaqueAdmin(admin.ModelAdmin):
    list_display = ("__str__", "capacidad_kg", "costo_nevera", "activo", "updated_at")
    list_editable = ("capacidad_kg", "costo_nevera", "activo")


@admin.register(PromocionEnvio)
class PromocionEnvioAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "umbral_subtotal",
        "jerarquia_maxima_cubierta",
        "tope_cubierto",
        "cubre_empaque",
        "activo",
        "updated_at",
    )
    list_editable = (
        "umbral_subtotal",
        "jerarquia_maxima_cubierta",
        "tope_cubierto",
        "cubre_empaque",
        "activo",
    )
