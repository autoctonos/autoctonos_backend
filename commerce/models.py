from django.db import models
from users.models import Usuario
from products.models import Producto
from locations.models import Municipio

ESTADO_CHOICES = [
    ('pendiente', 'Pendiente'),
    ('enviado', 'Enviado'),
    ('entregado', 'Entregado'),
    ('cancelado', 'Cancelado'),
]
ESTADO_PAGO_CHOICES = [
    ('pendiente', 'Pendiente'),
    ('aprobado', 'aprobado'),
    ('rechazado', 'rechazado'),
]
ESTADO_ENVIO_CHOICES = [
    ('preparación', 'Preparación'),
    ('camino', 'Camino'),
    ('entregado', 'Entregado'),
]

class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    # Checkout es guest: el comprador no siempre está logueado.
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )

    # Snapshot del comprador al momento de la compra (no depende de que exista un Usuario).
    comprador_nombre = models.CharField(max_length=255, default='')
    comprador_email = models.EmailField(default='')
    comprador_telefono = models.CharField(max_length=30, blank=True, default='')
    comprador_tipo_documento = models.CharField(max_length=20, blank=True, default='')
    comprador_documento = models.CharField(max_length=30, blank=True, default='')
    notas = models.TextField(blank=True, default='')

    # Snapshot del destino y de los totales de shipping.services.quote.TotalesCotizacion.
    id_municipio_destino = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, null=True, blank=True, related_name='pedidos',
    )
    municipio_destino_nombre = models.CharField(max_length=100, blank=True, default='')
    departamento_destino_nombre = models.CharField(max_length=100, blank=True, default='')

    subtotal_productos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    flete = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sobreflete = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    empaque = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento_envio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    envio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default='COP')

    # Espejo de ResultadoCotizacion.entrega: cuándo llega el último paquete del pedido.
    entrega_dias_min = models.PositiveSmallIntegerField(null=True, blank=True)
    entrega_dias_max = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        quien = self.id_usuario.username if self.id_usuario_id else self.comprador_nombre
        return f"Pedido {self.id_pedido} - {quien}"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-created_at']


class Envio(models.Model):
    """Una guía: todo lo que un productor despacha desde un mismo municipio de origen.

    Un Pedido puede tener varios Envios (uno por cada `GrupoEnvio` que devuelve
    `shipping.services.quote.cotizar`). La dirección/teléfono de entrega es una sola por
    pedido (vive en `Pedido`); lo que cambia por grupo es el origen y su tarifa.
    """
    id_envio = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True, related_name='envios')

    id_productor = models.ForeignKey(
        'productores.Productor', on_delete=models.PROTECT, related_name='envios',
    )
    id_municipio_origen = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='envios_origen',
    )

    # Snapshot del GrupoEnvio cotizado: nunca se recalcula después.
    trayecto_aplicado = models.CharField(max_length=20, default='')
    jerarquia = models.PositiveSmallIntegerField(default=0)
    peso_bruto_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    peso_facturable_kg = models.PositiveIntegerField(default=0)
    kilos_adicionales = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_kilo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_kilo_adicional = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    flete = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sobreflete = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    peso_frio_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    neveras = models.PositiveSmallIntegerField(default=0)
    empaque = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_grupo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    entrega_dias_min = models.PositiveSmallIntegerField(null=True, blank=True)
    entrega_dias_max = models.PositiveSmallIntegerField(null=True, blank=True)

    # Tracking logístico: ciclo de vida operativo, independiente del snapshot de cotización.
    estado = models.CharField(
        max_length=255, choices=ESTADO_ENVIO_CHOICES, default='preparación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Envio {self.id_envio} - Pedido {self.id_pedido_id} - {self.id_productor.nombre}"

    class Meta:
        verbose_name = "Envío"
        verbose_name_plural = "Envíos"
        ordering = ['-created_at']


class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=False, db_index=True)
    id_envio = models.ForeignKey(
        Envio, on_delete=models.CASCADE, null=True, blank=True, related_name='detalles',
        help_text="Grupo de envío (productor + origen) que despacha esta línea.",
    )
    cantidad = models.IntegerField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)

    # Snapshots: el producto puede cambiar de nombre/peso/categoría después de la compra.
    nombre_producto = models.CharField(max_length=255, blank=True, default='')
    peso_unitario_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    requiere_frio = models.BooleanField(default=False)

    def __str__(self):
        return f"Detalle de pedido {self.id_detalle_pedido} - {self.id_pedido.id_pedido} - {self.id_producto.nombre}"

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedidos"


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    metodo_pago = models.CharField(max_length=25, null=False)
    estado = models.CharField(
        max_length=25, choices=ESTADO_PAGO_CHOICES, default='pendiente')

    # Vínculo con PayU: referencia propia (no confiar en la que mande el cliente) +
    # lo que PayU devuelve en el webhook de confirmación.
    referencia_payu = models.CharField(max_length=64, unique=True, db_index=True)
    transaction_id = models.CharField(max_length=64, blank=True, default='')
    order_id_payu = models.CharField(max_length=64, blank=True, default='')
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default='COP')
    estado_payu = models.CharField(max_length=10, blank=True, default='')
    raw_response = models.JSONField(null=True, blank=True)
    firma_valida = models.BooleanField(default=False)
    confirmado_en = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        quien = self.id_usuario.username if self.id_usuario_id else self.referencia_payu
        return f"Pago {self.id_pago} - {self.id_pedido.id_pedido} - {quien}"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-created_at']
