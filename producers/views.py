from rest_framework import viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Productor, Municipio, Departamento
from .serializers import ProductorSerializer, MunicipioSerializer, DepartamentoSerializer


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class DepartamentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer


class MunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MunicipioSerializer

    def get_queryset(self):
        queryset = Municipio.objects.all()
        dep_id = self.request.query_params.get('departamento_id', None)
        if dep_id is not None:
            queryset = queryset.filter(id_departamento=dep_id)
        return queryset


class ProductorViewSet(viewsets.ModelViewSet):
    serializer_class = ProductorSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Productor.objects.all()
        municipio_id = self.request.query_params.get('id_municipio', None)
        departamento_id = self.request.query_params.get('departamento_id', None)
        if municipio_id:
            queryset = queryset.filter(id_municipio=municipio_id)
        elif departamento_id:
            queryset = queryset.filter(id_municipio__id_departamento=departamento_id)
        return queryset
