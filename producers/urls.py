from django.urls import path, include
from rest_framework import routers
from .views import ProductorViewSet

router = routers.DefaultRouter()
router.register(r'', ProductorViewSet)  # La ruta base será /api/productores/

urlpatterns = [
    path('', include(router.urls)),
]