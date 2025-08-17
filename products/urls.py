from django.urls import include, path
from .views import (
    ProductosConImagenView,
    ProductoViewSet,
    CategoriaViewSet,
    PostViewSet,
    ImagenProductoViewSet,
    ProductoDetalleView,
    DashboardCreateProductView,
)
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import routers, permissions

router = routers.DefaultRouter()

router.register(r'productos', ProductoViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'posts', PostViewSet)
router.register(r'imagenes_productos', ImagenProductoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('productos-con-imagenes/', ProductosConImagenView.as_view(), name='productos-con-imagenes'),
    path('producto-detalle/<int:pk>/', ProductoDetalleView.as_view({'get': 'retrieve'}), name='producto-detalle'),
    path('dashboard/create-product/', DashboardCreateProductView.as_view(), name='dashboard-create-product'),
]

