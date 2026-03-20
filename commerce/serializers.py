from rest_framework import serializers
from .models import Pedido, DetallePedido, Pago, Envio

class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = ['id_pedido', 'id_usuario', 'estado']

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = ['id_detalle_pedido', 'id_pedido', 'id_producto', 'cantidad', 'precio']

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ['id_pago', 'id_pedido', 'id_usuario', 'metodo_pago', 'estado']

class EnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Envio
        fields = ['id_envio', 'id_pedido', 'direccion', 'ciudad', 'codigo_postal', 'pais', 'telefono', 'estado']

