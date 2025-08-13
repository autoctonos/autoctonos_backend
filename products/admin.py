# admin.py
from django.contrib import admin, messages
from django.utils import timezone
from .models import Categoria, Producto

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


# -----------------------
# Admin de Producto
# -----------------------
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "id_categoria",
        "precio",
        "stock",
        "esta_publicado",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    list_filter = ("id_categoria", EstadoPublicadoFilter, "created_at")
    search_fields = ("nombre", "descripcion")
    actions = [publicar_productos, despublicar_productos]
    list_select_related = ("id_categoria",)
    autocomplete_fields = ("id_categoria",)  # <- ya funciona gracias a CategoriaAdmin con search_fields
    ordering = ("-created_at",)

    def esta_publicado(self, obj):
        return obj.deleted_at is None
    esta_publicado.boolean = True
    esta_publicado.short_description = "Publicado"
