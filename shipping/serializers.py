"""Contrato JSON del API de envíos. Frontera con el frontend: cambiar un nombre de
campo aquí rompe el checkout."""

from rest_framework import serializers


# ------------------------------------------------------------------- entrada

class ItemSolicitadoSerializer(serializers.Serializer):
    id_producto = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)


class CotizacionRequestSerializer(serializers.Serializer):
    id_municipio_destino = serializers.IntegerField(min_value=1)
    items = ItemSolicitadoSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        ids = [item['id_producto'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Hay productos repetidos en el carrito.")
        return value


# ------------------------------------------------------------------- destinos

class MunicipioDestinoSerializer(serializers.Serializer):
    id_municipio = serializers.IntegerField()
    nombre = serializers.CharField()
    trayecto = serializers.CharField()
    jerarquia = serializers.IntegerField()


class DepartamentoDestinoSerializer(serializers.Serializer):
    id_departamento = serializers.IntegerField()
    nombre = serializers.CharField()
    municipios = MunicipioDestinoSerializer(many=True)


class DestinosSerializer(serializers.Serializer):
    version = serializers.CharField()
    departamentos = DepartamentoDestinoSerializer(many=True)


# ------------------------------------------------------------------- salida

class DestinoSerializer(serializers.Serializer):
    id_municipio = serializers.IntegerField()
    nombre = serializers.CharField()
    departamento = serializers.CharField()
    trayecto = serializers.CharField(source='tarifa.codigo')
    jerarquia = serializers.IntegerField(source='tarifa.jerarquia')


class LineaCotizadaSerializer(serializers.Serializer):
    id_producto = serializers.IntegerField()
    nombre = serializers.CharField()
    cantidad = serializers.IntegerField()
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    peso_unitario_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2)
    requiere_frio = serializers.BooleanField()


class EntregaSerializer(serializers.Serializer):
    dias_min = serializers.IntegerField()
    dias_max = serializers.IntegerField()


class GrupoEnvioSerializer(serializers.Serializer):
    id_productor = serializers.IntegerField()
    productor = serializers.CharField()
    id_municipio_origen = serializers.IntegerField()
    municipio_origen = serializers.CharField()
    departamento_origen = serializers.CharField()
    trayecto_aplicado = serializers.CharField()
    jerarquia = serializers.IntegerField()
    entrega = EntregaSerializer()
    items = LineaCotizadaSerializer(many=True)
    peso_bruto_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    peso_facturable_kg = serializers.IntegerField()
    kilos_adicionales = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2)
    valor_kilo_inicial = serializers.DecimalField(max_digits=12, decimal_places=2)
    valor_kilo_adicional = serializers.DecimalField(max_digits=12, decimal_places=2)
    flete = serializers.DecimalField(max_digits=14, decimal_places=2)
    sobreflete = serializers.DecimalField(max_digits=14, decimal_places=2)
    peso_frio_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    neveras = serializers.IntegerField()
    empaque = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_grupo = serializers.DecimalField(max_digits=14, decimal_places=2)


class PromocionSerializer(serializers.Serializer):
    aplicada = serializers.BooleanField()
    umbral = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    descuento = serializers.DecimalField(max_digits=14, decimal_places=2)


class TotalesSerializer(serializers.Serializer):
    subtotal_productos = serializers.DecimalField(max_digits=14, decimal_places=2)
    flete = serializers.DecimalField(max_digits=14, decimal_places=2)
    sobreflete = serializers.DecimalField(max_digits=14, decimal_places=2)
    empaque = serializers.DecimalField(max_digits=14, decimal_places=2)
    descuento_envio = serializers.DecimalField(max_digits=14, decimal_places=2)
    envio = serializers.DecimalField(max_digits=14, decimal_places=2)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class CotizacionResponseSerializer(serializers.Serializer):
    destino = DestinoSerializer()
    grupos = GrupoEnvioSerializer(many=True)
    entrega = EntregaSerializer()
    promocion = PromocionSerializer()
    totales = TotalesSerializer()
    moneda = serializers.CharField(default='COP')
    generado_en = serializers.CharField()
