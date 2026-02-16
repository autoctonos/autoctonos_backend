from django.db import models
from users.models import Usuario

estado_choices = [
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
    ('revisión', 'Revisión'),
]


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    estado = models.CharField(max_length=10, choices=estado_choices, default='Revisión')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre
    
class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=False)
    url_imagen = models.ImageField(upload_to='productos_imagenes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)

class Post(models.Model):
    id_post = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=False)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    estado = models.CharField(max_length=10, choices=estado_choices, default='Revisión')
    mensaje = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)
    producto = models.OneToOneField(Producto, on_delete=models.SET_NULL, null=True, blank=True)

