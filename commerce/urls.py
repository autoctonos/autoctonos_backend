from django.urls import include, path
from .views import (
    CrearPedidoView,
    DetallePedidoViewSet,
    EnvioViewSet,
    PagoConfirmacionView,
    PagoViewSet,
    PedidoViewSet,
)
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import routers, permissions

router = routers.DefaultRouter()


router.register(r'pedidos', PedidoViewSet)
router.register(r'detalle_pedidos', DetallePedidoViewSet)
router.register(r'pagos', PagoViewSet)
router.register(r'envios', EnvioViewSet)

urlpatterns = [
    # Rutas literales antes del router: el lookup por defecto de DRF (`[^/.]+`) matchearía
    # "crear"/"confirmar" como si fuera un pk.
    path('pedidos/crear/', CrearPedidoView.as_view(), name='pedidos-crear'),
    path('pagos/confirmar/', PagoConfirmacionView.as_view(), name='pagos-confirmar'),
    path('', include(router.urls)),
]
