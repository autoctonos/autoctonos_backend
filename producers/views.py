from rest_framework import viewsets
from .models import Productor
from .serializers import ProductorSerializer

class ProductorViewSet(viewsets.ModelViewSet):
    queryset = Productor.objects.all()
    serializer_class = ProductorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()


        origen = self.request.query_params.get('origen', None)

        if origen is not None:
            queryset = queryset.filter(origen__icontains=origen)

        return queryset