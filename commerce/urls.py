from django.urls import include, path
from .views import PedidoViewSet, DetallePedidoViewSet, PagoViewSet, EnvioViewSet
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import routers, permissions

router = routers.DefaultRouter()


router.register(r'pedidos', PedidoViewSet)
router.register(r'detalle_pedidos', DetallePedidoViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'envios', EnvioViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

