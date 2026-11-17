import re

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

# Espejo de las reglas críticas de `astro_frontend/src/lib/validation/checkout.ts`. El
# front ya manda los valores normalizados; acá sólo se rechaza lo que no debe llegar a PayU.
_CELULAR_RE = re.compile(r'^3[0-35]\d{8}$')
_PESOS_NIT = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
TIPOS_DOCUMENTO = ('CC', 'CE', 'NIT', 'PP')  # códigos de PayU (`payerDocumentType`)


def digito_verificacion_nit(base: str) -> int:
    """Dígito de verificación de la DIAN (módulo 11)."""
    suma = sum(int(d) * p for d, p in zip(reversed(base), _PESOS_NIT))
    r = suma % 11
    return 11 - r if r > 1 else r


def _todos_iguales(s: str) -> bool:
    return len(set(s)) == 1


class CompradorSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=80)
    email = serializers.EmailField(max_length=254)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    tipo_documento = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    documento = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    def validate_nombre(self, valor):
        valor = ' '.join(valor.split())
        if any(c.isdigit() for c in valor):
            raise serializers.ValidationError('El nombre no puede tener números.')
        return valor

    def validate_email(self, valor):
        return valor.strip().lower()

    def validate_telefono(self, valor):
        if not valor:
            return valor
        digitos = re.sub(r'\D', '', valor)
        if len(digitos) == 12 and digitos.startswith('57'):
            digitos = digitos[2:]
        if not _CELULAR_RE.match(digitos) or _todos_iguales(digitos[3:]):
            raise serializers.ValidationError('Celular colombiano inválido: 10 dígitos que empiezan por 3.')
        return digitos

    def validate(self, datos):
        tipo = datos.get('tipo_documento', '')
        numero = datos.get('documento', '').strip().replace('.', '').replace(' ', '')
        if not tipo and not numero:
            return datos
        if tipo not in TIPOS_DOCUMENTO:
            raise serializers.ValidationError({'tipo_documento': 'Tipo de documento no válido.'})

        error = None
        if tipo in ('CC', 'CE'):
            if not re.fullmatch(r'[1-9]\d{4,9}', numero) or _todos_iguales(numero):
                error = 'Debe tener entre 5 y 10 dígitos, sin empezar por 0.'
        elif tipo == 'NIT':
            m = re.fullmatch(r'(\d{5,10})(?:-(\d))?', numero)
            if not m or _todos_iguales(m.group(1)):
                error = 'NIT inválido: entre 5 y 10 dígitos, con dígito de verificación opcional.'
            elif m.group(2) is not None and int(m.group(2)) != digito_verificacion_nit(m.group(1)):
                error = 'El dígito de verificación del NIT no coincide.'
        elif tipo == 'PP':
            numero = numero.upper()
            if not re.fullmatch(r'[A-Z0-9]{5,20}', numero) or not re.search(r'\d', numero):
                error = 'Pasaporte inválido: entre 5 y 20 letras y números.'
        if error:
            raise serializers.ValidationError({'documento': error})

        datos['documento'] = numero
        return datos


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
