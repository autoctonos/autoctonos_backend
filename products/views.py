from django.shortcuts import render, redirect
from rest_framework import viewsets, permissions
from .models import Producto, Categoria, ImagenProducto
from .serializers import (
    ProductoConImagenSerializer,
    ProductoSerializer,
    CategoriaSerializer,
    ImagenProductoSerializer,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import ProductoForm

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

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

class ProductosCategoriaView(APIView):
    def get(self, request):
        value = (request.query_params.get('id_categoria') or '').strip()
        qs = Producto.objects.all()

        if value:
            # si es numérico, filtra por ID; si no, por nombre (case-insensitive)
            if value.isdigit():
                qs = qs.filter(id_categoria=value)  # FK → acepta el PK directamente
            else:
                qs = qs.filter(id_categoria__nombre__iexact=value)

        serializer = ProductoConImagenSerializer(qs, many=True)  # ← NO tocamos lógica de imágenes
        return Response(serializer.data)


def staff_check(user):
    return user.is_staff


@login_required(login_url='/admin/login/')
@user_passes_test(staff_check)
def product_dashboard(request):
    """Simple dashboard to add and list products."""
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            imagen = form.cleaned_data.get('imagen')
            if imagen:
                ImagenProducto.objects.create(id_producto=producto, url_imagen=imagen)
            messages.success(request, 'Producto agregado correctamente.')
            return redirect('product-dashboard')
    else:
        form = ProductoForm()

    productos = Producto.objects.prefetch_related('imagenproducto_set').all()
    context = {
        'form': form,
        'productos': productos,
    }
    return render(request, 'products/dashboard.html', context)
