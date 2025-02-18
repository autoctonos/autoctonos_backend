from django.db import models
from users.models import Usuario

estado_choices = [
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
]


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre

class Post(models.Model):
    id_post = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    estado = models.CharField(max_length=10, choices=estado_choices, default='aprobado')
    mensaje_rechazo = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)
    
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    id_post = models.ForeignKey(Post, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre
    
class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    id_post = models.ForeignKey(Post, on_delete=models.CASCADE, null=False)
    url_imagen = models.ImageField(upload_to='productos_imagenes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)