from rest_framework import serializers

from shipping.serializers import ItemSolicitadoSerializer

from .models import DetallePedido, Envio, Pago, Pedido

class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = [
            'id_pedido', 'id_usuario', 'estado',
            'comprador_nombre', 'comprador_email', 'comprador_telefono',
            'municipio_destino_nombre', 'departamento_destino_nombre',
            'subtotal_productos', 'flete', 'sobreflete', 'empaque', 'descuento_envio',
            'envio', 'total', 'moneda', 'entrega_dias_min', 'entrega_dias_max',
            'created_at',
        ]

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = [
            'id_detalle_pedido', 'id_pedido', 'id_producto', 'id_envio',
            'cantidad', 'precio', 'nombre_producto', 'peso_unitario_kg', 'subtotal',
            'requiere_frio',
        ]

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = [
            'id_pago', 'id_pedido', 'id_usuario', 'metodo_pago', 'estado',
            'referencia_payu', 'monto', 'moneda', 'estado_payu', 'firma_valida',
            'confirmado_en',
        ]

class EnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Envio
        fields = [
            'id_envio', 'id_pedido', 'id_productor', 'id_municipio_origen',
            'trayecto_aplicado', 'jerarquia', 'peso_bruto_kg', 'peso_facturable_kg',
            'kilos_adicionales', 'subtotal', 'flete', 'sobreflete', 'peso_frio_kg',
            'neveras', 'empaque', 'total_grupo', 'entrega_dias_min', 'entrega_dias_max',
            'estado',
        ]


# --------------------------------------------------------------- crear pedido

class CompradorSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    tipo_documento = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    documento = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')


class CrearPedidoRequestSerializer(serializers.Serializer):
    comprador = CompradorSerializer()
    id_municipio_destino = serializers.IntegerField(min_value=1)
    items = ItemSolicitadoSerializer(many=True, allow_empty=False)
    notas = serializers.CharField(required=False, allow_blank=True, default='')


class CrearPedidoResponseSerializer(serializers.Serializer):
    id_pedido = serializers.IntegerField()
    referencia_payu = serializers.CharField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    moneda = serializers.CharField()
