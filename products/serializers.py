from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Producto, Categoria, Post, ImagenProducto 
from django.conf import settings

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'id_post', 'nombre', 'descripcion', 'precio', 'stock']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']
        
class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id_post', 'id_usuario', 'nombre', 'descripcion', 'precio', 'stock']

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id_post', 'id_usuario', 'nombre', 'descripcion', 'precio', 'stock', 'estado', 'mensaje', 'created_at']

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'id_post', 'url_imagen', 'created_at']
        
class ProductoConImagenSerializer(serializers.ModelSerializer):
    imagenes = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'id_post', 'nombre', 'descripcion', 'precio', 'stock', 'imagenes']

    def get_imagenes(self, obj):
        imagenes = ImagenProducto.objects.filter(id_post=obj.id_post)
        return ImagenProductoSerializer(imagenes, many=True).data
