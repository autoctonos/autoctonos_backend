from rest_framework import status, viewsets, permissions
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from shipping.services.exceptions import ErrorCotizacion

from .models import Pedido, DetallePedido, Pago, Envio
from .serializers import (
    CrearPedidoRequestSerializer,
    CrearPedidoResponseSerializer,
    DetallePedidoSerializer,
    EnvioSerializer,
    PagoSerializer,
    PedidoSerializer,
)
from .services.order_creation import crear_pedido_pendiente
from .services.payu_confirmation import procesar_confirmacion, verificar_firma


class IsAdminOrOwner(BasePermission):
    """Admins pueden todo. Usuarios solo ven/modifican sus propios registros."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, 'id_usuario'):
            return obj.id_usuario == request.user
        if hasattr(obj, 'id_pedido') and hasattr(obj.id_pedido, 'id_usuario'):
            return obj.id_pedido.id_usuario == request.user
        return False


class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Pedido.objects.all()
        return Pedido.objects.filter(id_usuario=user)


class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return DetallePedido.objects.all()
        return DetallePedido.objects.filter(id_pedido__id_usuario=user)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Pago.objects.all()
        return Pago.objects.filter(id_pedido__id_usuario=user)


class EnvioViewSet(viewsets.ModelViewSet):
    queryset = Envio.objects.all()
    serializer_class = EnvioSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Envio.objects.all()
        return Envio.objects.filter(id_pedido__id_usuario=user)


class CrearPedidoView(APIView):
    """Cotiza server-side (mismo camino que `shipping.views.CotizarView`) y crea
    Pedido + Envio(s) + DetallePedido + Pago pendiente de forma atómica.

    Checkout guest: no exige JWT. El comprador se guarda como snapshot en `Pedido`.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'crear_pedido'

    def post(self, request):
        peticion = CrearPedidoRequestSerializer(data=request.data)
        peticion.is_valid(raise_exception=True)

        datos = dict(peticion.validated_data)
        if request.user and request.user.is_authenticated:
            datos['id_usuario'] = request.user

        try:
            pedido, pago = crear_pedido_pendiente(datos)
        except ErrorCotizacion as error:
            return Response(error.as_dict(), status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        serializer = CrearPedidoResponseSerializer({
            'id_pedido': pedido.id_pedido,
            'referencia_payu': pago.referencia_payu,
            'total': pedido.total,
            'moneda': pedido.moneda,
        })
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PagoConfirmacionView(APIView):
    """Recibe el webhook de confirmación de PayU (reenviado por
    `astro_frontend/src/pages/api/payu/confirmation.ts`), verifica la firma y actualiza
    Pago/Pedido de forma idempotente. Siempre responde 200 salvo payload inválido: PayU
    reintenta si no recibe 200, y no conviene darle pistas a quien mande una firma
    inválida sobre por qué falló.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'confirmar_pago'

    def post(self, request):
        payload = request.data
        if not isinstance(payload, dict) or not payload.get('reference_sale'):
            return Response({'detail': 'Payload inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        firma_valida = verificar_firma(payload)
        procesar_confirmacion(payload, firma_valida)
        return Response({'ok': True})