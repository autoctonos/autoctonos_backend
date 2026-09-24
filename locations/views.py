from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Departamento, Municipio
from .serializers import DepartamentoSerializer, MunicipioSerializer


class DepartamentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Departamento.objects.all().order_by('nombre')
    serializer_class = DepartamentoSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class MunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MunicipioSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Municipio.objects.select_related('id_departamento').order_by('nombre')
        departamento_id = self.request.query_params.get('departamento_id')
        if departamento_id:
            queryset = queryset.filter(id_departamento=departamento_id)
        return queryset
