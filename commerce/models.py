from django.db import models
from users.models import Usuario
from products.models import Producto

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
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=False, db_index=True)
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"Pedido {self.id_pedido} - {self.id_usuario.username}"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-created_at']


class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=False, db_index=True)
    cantidad = models.IntegerField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)

    def __str__(self):
        return f"Detalle de pedido {self.id_detalle_pedido} - {self.id_pedido.id_pedido} - {self.id_producto.nombre}"

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedidos"


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=False, db_index=True)
    metodo_pago = models.CharField(max_length=25, null=False)
    estado = models.CharField(
        max_length=25, choices=ESTADO_PAGO_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pago {self.id_pago} - {self.id_pedido.id_pedido} - {self.id_usuario.username}"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-created_at']


class Envio(models.Model):
    id_envio = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=False, db_index=True)
    direccion = models.CharField(max_length=255, null=False)
    ciudad = models.CharField(max_length=255, null=False)
    codigo_postal = models.CharField(max_length=255)
    pais = models.CharField(max_length=255, null=False)
    telefono = models.CharField(max_length=255, null=False)
    estado = models.CharField(
        max_length=255, choices=ESTADO_ENVIO_CHOICES, default='preparación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Envio {self.id_envio} - {self.ciudad}, {self.pais}"

    class Meta:
        verbose_name = "Envío"
        verbose_name_plural = "Envíos"
        ordering = ['-created_at']
