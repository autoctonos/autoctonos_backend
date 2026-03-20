from django.urls import path, include
from rest_framework import routers
from .views import ProductorViewSet, MunicipioViewSet, DepartamentoViewSet

router = routers.DefaultRouter()
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'municipios', MunicipioViewSet, basename='municipio')
router.register(r'', ProductorViewSet, basename='productor')

urlpatterns = [
    path('', include(router.urls)),
]