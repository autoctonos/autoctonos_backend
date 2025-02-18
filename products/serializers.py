from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Producto, Categoria, Post, ImagenProducto

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'id_post', 'nombre', 'descripcion', 'precio', 'stock']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id_post', 'id_usuario', 'nombre', 'descripcion', 'precio', 'stock', 'estado', 'mensaje_rechazo']

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'id_post', 'url_imagen']
