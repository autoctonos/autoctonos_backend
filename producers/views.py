from rest_framework import viewsets
from .models import Productor
from .serializers import ProductorSerializer

class ProductorViewSet(viewsets.ModelViewSet):
    queryset = Productor.objects.all()
    serializer_class = ProductorSerializer