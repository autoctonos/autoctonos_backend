from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Producto, Categoria, Post

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'id_post', 'nombre', 'descripcion', 'precio', 'stock', 'imagen']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id_post', 'id_usuario', 'nombre']

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'id_producto', 'url_imagen']
