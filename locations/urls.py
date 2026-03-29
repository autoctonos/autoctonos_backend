from django.urls import path, include
from rest_framework import routers
from .views import DepartamentoViewSet, MunicipioViewSet

router = routers.DefaultRouter()
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'municipios', MunicipioViewSet, basename='municipio')

urlpatterns = [
    path('', include(router.urls)),
]
