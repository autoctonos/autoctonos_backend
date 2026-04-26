# admin.py
from django.contrib import admin, messages
from django.utils import timezone
from django import forms
from .models import Categoria, Producto, ImagenProducto

# -----------------------
# Admin de Categoria (NECESARIO para autocomplete_fields en ProductoAdmin)
# -----------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)         # <- requerido para que autocomplete_fields funcione
    list_display = ("nombre",)
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

class ProductoAdminForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        exclude = ['deleted_at']  # Ocultar deleted_at del formulario
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'updated_at' in self.fields:
            self.fields['updated_at'].required = False
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
        "id_municipio",
        "fabricante",
        "es_promocionado_display",
        "esta_publicado",
        "created_at",
        "updated_at",
        "fecha_eliminacion",
    )
    list_filter = ("id_categoria", EstadoPublicadoFilter, "es_promocionado", "created_at", "id_municipio__id_departamento", "id_municipio")
    search_fields = ("nombre", "descripcion", "fabricante", "id_municipio__nombre", "id_municipio__id_departamento__nombre")
    actions = [publicar_productos, despublicar_productos, marcar_promocionados, desmarcar_promocionados]
    list_select_related = ("id_categoria", "id_municipio", "id_municipio__id_departamento")
    autocomplete_fields = ("id_categoria", "id_municipio")
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
