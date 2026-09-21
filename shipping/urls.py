from django.urls import path

from .views import CotizarView, DestinosView

urlpatterns = [
    path('destinos/', DestinosView.as_view(), name='envios-destinos'),
    path('cotizar/', CotizarView.as_view(), name='envios-cotizar'),
]
