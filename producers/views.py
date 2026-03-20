from rest_framework import viewsets
from .models import Productor
from .serializers import ProductorSerializer
from .models import Productor, Municipio, Departamento
from .serializers import ProductorSerializer, MunicipioSerializer, DepartamentoSerializer

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

    def get_queryset(self):
        queryset = Productor.objects.all()


        municipio_id = self.request.query_params.get('id_municipio', None)
        departamento_id = self.request.query_params.get('departamento_id', None)

        if municipio_id:
            queryset = queryset.filter(id_municipio=municipio_id)
        elif departamento_id:
            queryset = queryset.filter(id_municipio__id_departamento=departamento_id)

        return queryset