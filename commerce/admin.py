from django.contrib import admin, messages
from django.utils import timezone
from datetime import timedelta
from .models import Pedido, DetallePedido, Pago, Envio


# -----------------------
# Filtros personalizados de fecha
# -----------------------
class FechaRecenteFilter(admin.SimpleListFilter):
    title = "período"
    parameter_name = "periodo"

    def lookups(self, request, model_admin):
        return (
            ("7d", "Últimos 7 días"),
            ("30d", "Últimos 30 días"),
            ("mes_actual", "Mes actual"),
            ("mes_anterior", "Mes anterior"),
        )

    def queryset(self, request, queryset):
        hoy = timezone.now()
        if self.value() == "7d":
            return queryset.filter(created_at__gte=hoy - timedelta(days=7))
        if self.value() == "30d":
            return queryset.filter(created_at__gte=hoy - timedelta(days=30))
        if self.value() == "mes_actual":
            return queryset.filter(created_at__year=hoy.year, created_at__month=hoy.month)
        if self.value() == "mes_anterior":
            primer_dia_mes = hoy.replace(day=1)
            ultimo_mes = primer_dia_mes - timedelta(days=1)
            return queryset.filter(created_at__year=ultimo_mes.year, created_at__month=ultimo_mes.month)
        return queryset


# -----------------------
# Acciones masivas sobre Pedido
# -----------------------
@admin.action(description="Marcar pedidos seleccionados como entregados")
def marcar_entregado(modeladmin, request, queryset):
    actualizados = queryset.update(estado="entregado")
    messages.success(request, f"{actualizados} pedido(s) marcados como entregados.")


@admin.action(description="Cancelar pedidos seleccionados")
def cancelar_pedidos(modeladmin, request, queryset):
    actualizados = queryset.update(estado="cancelado")
    messages.warning(request, f"{actualizados} pedido(s) cancelados.")


# -----------------------
# Inline: DetallePedido dentro de Pedido
# -----------------------
class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    fields = ("id_producto", "cantidad", "precio")
    readonly_fields = ("id_producto", "cantidad", "precio")
    can_delete = False
    show_change_link = True


# -----------------------
# Admin de Pedido
# -----------------------
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id_pedido", "id_usuario", "estado", "num_items", "created_at", "updated_at")
    list_filter = (FechaRecenteFilter, "estado")
    search_fields = ("id_usuario__username", "id_usuario__email")
    ordering = ("-created_at",)
    list_select_related = ("id_usuario",)
    list_per_page = 20
    list_max_show_all = 100
    show_full_result_count = False
    actions = [marcar_entregado, cancelar_pedidos]
    inlines = [DetallePedidoInline]
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Por defecto mostrar solo últimos 30 días si no hay filtro activo
        if not request.GET.get("periodo") and not request.GET.get("estado"):
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
        return qs

    def num_items(self, obj):
        return obj.detallepedido_set.count()
    num_items.short_description = "Artículos"


# -----------------------
# Admin de DetallePedido
# -----------------------
@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("id_detalle_pedido", "id_pedido", "id_producto", "cantidad", "precio")
    search_fields = ("id_pedido__id_pedido", "id_producto__nombre")
    list_select_related = ("id_pedido", "id_pedido__id_usuario", "id_producto")
    list_per_page = 50
    list_max_show_all = 200
    show_full_result_count = False


# -----------------------
# Admin de Pago
# -----------------------
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id_pago", "id_pedido", "id_usuario", "metodo_pago", "estado", "created_at")
    list_filter = (FechaRecenteFilter, "estado", "metodo_pago")
    search_fields = ("id_usuario__username", "id_usuario__email", "id_pedido__id_pedido")
    ordering = ("-created_at",)
    list_select_related = ("id_pedido", "id_usuario")
    list_per_page = 20
    list_max_show_all = 100
    show_full_result_count = False
    date_hierarchy = "created_at"


# -----------------------
# Admin de Envio
# -----------------------
@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ("id_envio", "id_pedido", "ciudad", "pais", "estado", "created_at")
    list_filter = (FechaRecenteFilter, "estado", "pais")
    search_fields = ("ciudad", "pais", "id_pedido__id_pedido", "id_pedido__id_usuario__username")
    ordering = ("-created_at",)
    list_select_related = ("id_pedido", "id_pedido__id_usuario")
    list_per_page = 20
    list_max_show_all = 100
    show_full_result_count = False
    date_hierarchy = "created_at"
