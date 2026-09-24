from rest_framework import serializers
from .models import Departamento, Municipio


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id_departamento', 'nombre']


class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ['id_municipio', 'id_departamento', 'nombre']
