from django.contrib import admin
from .models import Pedido, DetallePedido, Pago, Envio


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id_pedido', 'id_usuario', 'estado', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['id_usuario__username', 'id_usuario__email']
    ordering = ['-created_at']


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ['id_detalle_pedido', 'id_pedido', 'id_producto', 'cantidad', 'precio']
    search_fields = ['id_pedido__id_pedido', 'id_producto__nombre']


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['id_pago', 'id_pedido', 'id_usuario', 'metodo_pago', 'estado', 'created_at']
    list_filter = ['estado', 'metodo_pago']
    search_fields = ['id_usuario__username', 'id_pedido__id_pedido']
    ordering = ['-created_at']


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ['id_envio', 'id_pedido', 'ciudad', 'pais', 'estado', 'created_at']
    list_filter = ['estado', 'pais']
    search_fields = ['ciudad', 'pais', 'id_pedido__id_pedido']
    ordering = ['-created_at']
