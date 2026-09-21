from datetime import timezone as tz

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import CotizacionRequestSerializer, CotizacionResponseSerializer, DestinosSerializer
from .services.exceptions import ErrorCotizacion
from .services.quote import cotizar
from .services.repository import construir_entrada, destinos_por_departamento


def _iso(momento):
    return momento.astimezone(tz.utc).isoformat().replace('+00:00', 'Z')


class DestinosView(APIView):
    """Municipios a los que se puede despachar, agrupados por departamento."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'envios_destinos'
    pagination_class = None

    def get(self, request):
        departamentos, version = destinos_por_departamento()
        serializer = DestinosSerializer({
            'version': _iso(version or timezone.now()),
            'departamentos': departamentos,
        })
        respuesta = Response(serializer.data)
        respuesta['Cache-Control'] = 'public, max-age=3600'
        return respuesta


class CotizarView(APIView):
    """Cotiza flete + sobreflete + empaque. Sólo acepta ids y cantidades: precios,
    pesos y orígenes se resuelven contra la base de datos."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'cotizacion'

    def post(self, request):
        peticion = CotizacionRequestSerializer(data=request.data)
        peticion.is_valid(raise_exception=True)

        try:
            entrada = construir_entrada(
                peticion.validated_data['id_municipio_destino'],
                peticion.validated_data['items'],
            )
        except ErrorCotizacion as error:
            return Response(error.as_dict(), status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        resultado = cotizar(entrada)
        serializer = CotizacionResponseSerializer({
            'destino': resultado.destino,
            'grupos': resultado.grupos,
            'entrega': resultado.entrega,
            'promocion': resultado.promocion,
            'totales': resultado.totales,
            'moneda': 'COP',
            'generado_en': _iso(timezone.now()),
        })
        return Response(serializer.data)
