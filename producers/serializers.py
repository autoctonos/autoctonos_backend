from rest_framework import serializers
from .models import Productor

class ProductorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Productor
        fields = ['id_productor', 'nombre', 'descripcion', 'imagen', 'origen', 'created_at']