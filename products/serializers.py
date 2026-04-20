from rest_framework import serializers
from .models import Producto, Categoria, ImagenProducto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']


class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'id_producto', 'url_imagen', 'created_at']


class ProductoSerializer(serializers.ModelSerializer):
    productor_nombre = serializers.CharField(source='id_productor.nombre', read_only=True, default=None)

    class Meta:
        model = Producto
        fields = ['id_producto', 'id_productor', 'productor_nombre', 'id_categoria', 'nombre', 'descripcion', 'precio', 'stock', 'created_at']
        extra_kwargs = {
            'id_productor': {'required': True, 'allow_null': False},
        }

    def validate_precio(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo.")
        return value

    def validate_porcentaje_descuento(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("El porcentaje de descuento debe estar entre 0 y 100.")
        return value

    def validate_id_productor(self, value):
        if value is None:
            raise serializers.ValidationError("El productor es obligatorio.")
        return value


class ProductoConImagenSerializer(serializers.ModelSerializer):
    imagenes = serializers.SerializerMethodField()
    precio_con_descuento = serializers.SerializerMethodField()
    presentacion_completa = serializers.SerializerMethodField()
    productor_nombre = serializers.CharField(source='id_productor.nombre', read_only=True, default=None)
    productor_ubicacion = serializers.CharField(source='id_productor.ubicacion_completa', read_only=True, default=None)

    class Meta:
        model = Producto
        fields = [
            'id_producto', 'id_productor', 'productor_nombre', 'productor_ubicacion',
            'id_categoria', 'nombre', 'descripcion',
            'precio', 'precio_con_descuento', 'es_promocionado', 'porcentaje_descuento',
            'stock', 'presentacion', 'cantidad_presentacion', 'presentacion_completa',
            'fabricante', 'imagenes', 'created_at',
        ]

    def get_imagenes(self, obj):
        imagenes = obj.imagenproducto_set.all()
        return ImagenProductoSerializer(imagenes, many=True).data

    def get_precio_con_descuento(self, obj):
        if obj.es_promocionado and obj.porcentaje_descuento:
            return str(obj.precio_con_descuento())
        return None

    def get_presentacion_completa(self, obj):
        return obj.get_presentacion_completa()


class ProductoByCategoriaSerializer(serializers.ModelSerializer):
    imagenes = serializers.SerializerMethodField()
    productor_nombre = serializers.CharField(source='id_productor.nombre', read_only=True, default=None)

    class Meta:
        model = Producto
        fields = ['id_producto', 'id_productor', 'productor_nombre', 'nombre', 'descripcion', 'precio', 'stock', 'imagenes']

    def get_imagenes(self, obj):
        imagenes = obj.imagenproducto_set.all()
        return ImagenProductoSerializer(imagenes, many=True).data
