# admin.py
from django.contrib import admin, messages
from django.db.models import Q
from django.utils import timezone
from django import forms
from .models import Categoria, Producto, ImagenProducto

# -----------------------
# Admin de Categoria (NECESARIO para autocomplete_fields en ProductoAdmin)
# -----------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)         # <- requerido para que autocomplete_fields funcione
    list_display = ("nombre", "requiere_frio")
    list_editable = ("requiere_frio",)
    list_filter = ("requiere_frio",)
    ordering = ("nombre",)


# -----------------------
# Acciones sobre Producto
# -----------------------
@admin.action(description="Publicar productos seleccionados")
def publicar_productos(modeladmin, request, queryset):
    actualizados = queryset.update(deleted_at=None, updated_at=timezone.now())
    messages.success(request, f"Productos publicados: {actualizados}")

@admin.action(description="Despublicar productos seleccionados")
def despublicar_productos(modeladmin, request, queryset):
    actualizados = queryset.update(deleted_at=timezone.now())
    messages.warning(request, f"Productos despublicados: {actualizados}")

@admin.action(description="Marcar como promocionados")
def marcar_promocionados(modeladmin, request, queryset):
    actualizados = queryset.update(es_promocionado=True, updated_at=timezone.now())
    messages.success(request, f"Productos marcados como promocionados: {actualizados}")

@admin.action(description="Desmarcar como promocionados")
def desmarcar_promocionados(modeladmin, request, queryset):
    actualizados = queryset.update(es_promocionado=False, updated_at=timezone.now())
    messages.info(request, f"Productos desmarcados como promocionados: {actualizados}")

class EstadoPublicadoFilter(admin.SimpleListFilter):
    title = "estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return (
            ("publicado", "Publicado"),
            ("despublicado", "Despublicado"),
        )

    def queryset(self, request, queryset):
        if self.value() == "publicado":
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == "despublicado":
            return queryset.filter(deleted_at__isnull=False)
        return queryset

class ReadinessEnviosFilter(admin.SimpleListFilter):
    """Qué le falta a un producto para poder cotizarse."""

    title = "listo para envíos"
    parameter_name = "envios"

    def lookups(self, request, model_admin):
        return (
            ("sin_peso", "Falta peso"),
            ("sin_productor", "Falta productor"),
            ("sin_origen", "Falta origen"),
            ("origen_sin_cobertura", "Origen sin cobertura"),
            ("despachable", "Despachable"),
        )

    def queryset(self, request, queryset):
        # El origen es el override del producto y, si está vacío, el municipio del
        # productor. Los dos Q de abajo son esa misma regla, escrita en el ORM.
        tiene_origen = Q(id_municipio__isnull=False) | Q(id_productor__id_municipio__isnull=False)
        cobertura_ok = Q(
            id_municipio__cobertura__activo=True,
            id_municipio__cobertura__trayecto_origen__isnull=False,
        ) | Q(
            id_municipio__isnull=True,
            id_productor__id_municipio__cobertura__activo=True,
            id_productor__id_municipio__cobertura__trayecto_origen__isnull=False,
        )
        if self.value() == "sin_peso":
            return queryset.filter(peso_kg__isnull=True)
        if self.value() == "sin_productor":
            return queryset.filter(id_productor__isnull=True)
        if self.value() == "sin_origen":
            return queryset.exclude(tiene_origen)
        if self.value() == "origen_sin_cobertura":
            return queryset.filter(tiene_origen).exclude(cobertura_ok)
        if self.value() == "despachable":
            return queryset.filter(tiene_origen, cobertura_ok, peso_kg__isnull=False)
        return queryset


class ProductoAdminForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        exclude = ['deleted_at']  # Ocultar deleted_at del formulario
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'updated_at' in self.fields:
            self.fields['updated_at'].required = False
        # El origen sale del productor; el municipio es sólo un override.
        self.fields['id_productor'].required = True
        self.fields['id_municipio'].required = False
        self.fields['fabricante'].required = False

class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 2
    min_num = 2
    max_num = 4
    fields = ('url_imagen',)
    verbose_name = "Imagen"
    verbose_name_plural = "Imágenes (mínimo 2, máximo 4)"


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    inlines = [ImagenProductoInline]
    form = ProductoAdminForm
    list_display = (
        "nombre",
        "id_categoria",
        "precio",
        "precio_con_descuento_display",
        "stock",
        "presentacion_completa_display",
        "peso_kg",
        "requiere_frio_display",
        "id_productor",
        "id_municipio",
        "fabricante",
        "es_promocionado_display",
        "esta_publicado",
        "created_at",
        "updated_at",
        "fecha_eliminacion",
    )
    list_editable = ("peso_kg",)
    list_filter = ("id_categoria", EstadoPublicadoFilter, ReadinessEnviosFilter, "requiere_frio_override", "es_promocionado", "created_at", "id_productor", "id_municipio__id_departamento", "id_municipio")
    search_fields = ("nombre", "descripcion", "fabricante", "id_productor__nombre", "id_municipio__nombre", "id_municipio__id_departamento__nombre")
    actions = [publicar_productos, despublicar_productos, marcar_promocionados, desmarcar_promocionados]
    list_select_related = ("id_categoria", "id_productor", "id_productor__id_municipio", "id_municipio", "id_municipio__id_departamento")
    autocomplete_fields = ("id_categoria", "id_productor", "id_municipio")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        # Por defecto mostrar solo productos no eliminados
        # El filtro EstadoPublicadoFilter permitirá ver los eliminados si se selecciona
        qs = super().get_queryset(request)
        # Si no hay filtro activo, mostrar solo no eliminados
        if not request.GET.get('estado'):
            qs = qs.filter(deleted_at__isnull=True)
        return qs

    def esta_publicado(self, obj):
        return obj.deleted_at is None
    esta_publicado.boolean = True
    esta_publicado.short_description = "Publicado"
    
    def requiere_frio_display(self, obj):
        return obj.requiere_frio
    requiere_frio_display.boolean = True
    requiere_frio_display.short_description = "Cadena de frío"

    def presentacion_completa_display(self, obj):
        return obj.get_presentacion_completa()
    presentacion_completa_display.short_description = "Presentación"

    def es_promocionado_display(self, obj):
        return obj.es_promocionado
    es_promocionado_display.boolean = True
    es_promocionado_display.short_description = "Promocionado"
    
    def precio_con_descuento_display(self, obj):
        if obj.es_promocionado and obj.porcentaje_descuento:
            precio_original = obj.precio
            precio_descuento = obj.precio_con_descuento()
            return f"{precio_original} → {precio_descuento} (-{obj.porcentaje_descuento}%)"
        return "-"
    precio_con_descuento_display.short_description = "Precio con Descuento"

    def fecha_eliminacion(self, obj):
        if obj.deleted_at:
            return obj.deleted_at.strftime("%Y-%m-%d %H:%M:%S")
        return "-"
    fecha_eliminacion.short_description = "Fecha de Eliminación"

    def delete_model(self, request, obj):
        """
        Sobrescribir el método delete para hacer soft delete.
        En lugar de eliminar físicamente, marca deleted_at con la fecha/hora actual.
        """
        obj.deleted_at = timezone.now()
        obj.updated_at = timezone.now()
        obj.save()
        messages.success(request, f'El producto "{obj.nombre}" ha sido marcado como eliminado.')

    def delete_queryset(self, request, queryset):
        """
        Sobrescribir para hacer soft delete en múltiples objetos.
        """
        count = queryset.update(deleted_at=timezone.now(), updated_at=timezone.now())
        messages.success(request, f'{count} producto(s) han sido marcados como eliminados.')
