from rest_framework import serializers
from .models import Producto, Categoria, ImagenProducto

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'nombre', 'descripcion', 'precio', 'stock']

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

    class Meta:
        model = Producto
        fields = ['id_producto', 'id_categoria', 'nombre', 'descripcion', 'precio', 'stock', 'imagenes']

    def get_imagenes(self, obj):
        imagenes = ImagenProducto.objects.filter(id_producto=obj)
        return ImagenProductoSerializer(imagenes, many=True).data
