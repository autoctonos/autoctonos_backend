from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import Producto, Categoria, Post, ImagenProducto
from .serializers import ProductoConImagenSerializer, PostCreateSerializer, ProductoSerializer, CategoriaSerializer, PostSerializer, ImagenProductoSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response 
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all() 
    
    def get_queryset(self):
        queryset = super().get_queryset()
       
        id_usuario = self.request.query_params.get('id_usuario', None)
        if id_usuario is not None:
            queryset = queryset.filter(id_usuario=id_usuario)
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateSerializer
        return PostSerializer

class ImagenProductoViewSet(viewsets.ModelViewSet):
    queryset = ImagenProducto.objects.all()
    serializer_class = ImagenProductoSerializer

class ProductosConImagenView(APIView):
    def get(self, request):
        productos = Producto.objects.all()[:8]  
        serializer = ProductoConImagenSerializer(productos, many=True)
        return Response(serializer.data)

class ProductoDetalleView(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoConImagenSerializer

    def retrieve(self, request, pk=None):
        try:
            producto = self.get_object()
            serializer = self.get_serializer(producto)
            return Response(serializer.data)
        except Producto.DoesNotExist:
            return Response({"message": "Producto no encontrado."})


class DashboardCreateProductView(generics.CreateAPIView):
    """Create a Post from the dashboard with default review state."""

    queryset = Post.objects.all()
    serializer_class = PostCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["id_usuario"] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(
            id_usuario=self.request.user,
            estado="revisión",
            mensaje="En revisión",
        )
