from django.db import models
from django.contrib.auth.models import User
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
    ('pendiente', 'Pendiente'),
    ('enviado', 'Enviado'),
    ('entregado', 'Entregado'),
    ('cancelado', 'Cancelado'),
]


class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"Pedido {self.id_pedido} - {self.id_usuario.username}"


class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detalle de pedido {self.id_detalle_pedido} - {self.id_pedido.id_pedido} - {self.id_producto.nombre}"


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    metodo_pago = models.CharField(max_length=25)
    estado = models.CharField(
        max_length=25, choices=ESTADO_PAGO_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"Pago {self.id_pago} - {self.id_pedido.id_pedido} - {self.id_usuario.username}"


class Envio(models.Model):
    id_envio = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=255)
    codigo_postal = models.CharField(max_length=255)
    pais = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    estado = models.CharField(
        max_length=255, choices=ESTADO_ENVIO_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"Envio {self.id_envio} - {self.id_pedido.id_pedido} - {self.direccion} - {self.ciudad} - {self.codigo_postal} - {self.pais} - {self.telefono}"
