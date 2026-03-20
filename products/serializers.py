from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Producto, Categoria, ImagenProducto 
from django.conf import settings

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'nombre', 'descripcion', 'precio', 'stock', 'estado', 'created_at']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'id_producto', 'url_imagen', 'created_at']
        
class ProductoConImagenSerializer(serializers.ModelSerializer):
    imagenes = serializers.SerializerMethodField()
    precio_con_descuento = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id_producto', 'id_categoria', 'nombre', 'descripcion',
            'precio', 'precio_con_descuento', 'es_promocionado', 'porcentaje_descuento',
            'stock', 'imagenes',
        ]

    def get_imagenes(self, obj):
        imagenes = ImagenProducto.objects.filter(id_producto=obj.id_producto)
        return ImagenProductoSerializer(imagenes, many=True).data

    def get_precio_con_descuento(self, obj):
        """Returns the discounted price as a string, or null when there is no active promotion."""
        if obj.es_promocionado and obj.porcentaje_descuento:
            return str(obj.precio_con_descuento())
        return None

class ProductoByCategoriaSerializer(serializers.ModelSerializer):
    productos_categoria = serializers.SerializerMethodField()
    class Meta:
        model = Producto
        fields = ['id_producto','nombre','descripcion','precio','stock','imagenes']
