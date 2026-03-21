from rest_framework import serializers
from .models import Productor, Municipio, Departamento

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id_departamento', 'nombre']

class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ['id_municipio', 'id_departamento', 'nombre']

class ProductorSerializer(serializers.ModelSerializer):
    ubicacion = serializers.CharField(source='ubicacion_completa', read_only=True)
    municipio_nombre = serializers.CharField(source='id_municipio.nombre', read_only=True, default=None)
    departamento_nombre = serializers.CharField(
        source='id_municipio.id_departamento.nombre', read_only=True, default=None
    )

    class Meta:
        model = Productor
        fields = [
            'id_productor',
            'nombre',
            'descripcion',
            'imagen',
            'id_municipio',
            'municipio_nombre',
            'departamento_nombre',
            'ubicacion',
            'created_at',
        ]