from rest_framework import viewsets, permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Pedido, DetallePedido, Pago, Envio
from .serializers import PedidoSerializer, DetallePedidoSerializer, PagoSerializer, EnvioSerializer


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