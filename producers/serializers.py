from rest_framework import serializers
from .models import Productor, Municipio, Departamento

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id_departamento', 'nombre']

class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ['id_municipio', 'nombre']

class ProductorSerializer(serializers.ModelSerializer):

    ubicacion = serializers.CharField(source='ubicacion_completa', read_only=True)

    class Meta:
        model = Productor
        fields = [
            'id_productor',
            'nombre',
            'descripcion',
            'imagen',
            'id_municipio',
            'ubicacion',
            'created_at'
        ]