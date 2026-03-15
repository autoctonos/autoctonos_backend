from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.conf import settings
from rest_framework import viewsets, permissions
from django.contrib import messages
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
from django.contrib.auth.decorators import login_required
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


def admin_check(user):
    return user.is_staff


@login_required(login_url='/admin/login/')
def product_dashboard(request):
    """Dashboard to add and list products with optional image upload."""
    if not admin_check(request.user):
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            image = form.cleaned_data.get('image')
            if image:
                ImagenProducto.objects.create(id_producto=producto, url_imagen=image)
            messages.success(request, 'Product added successfully!')
            return redirect('product-dashboard')
        else:
            if hasattr(settings, 'DEBUG') and settings.DEBUG:
                import pprint
                print("Form errors:", pprint.pformat(form.errors))
                print("Form data:", pprint.pformat(form.data))
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductoForm()

    queryset = Producto.objects.all().order_by("-created_at")
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)
    context = {
        "form": form,
        "page": page,
        "productos": page.object_list,
    }
    return render(request, "products/dashboard.html", context)


@login_required(login_url='/admin/login/')
def product_update(request, pk):
    if not admin_check(request.user):
        return HttpResponseForbidden()
    producto = get_object_or_404(Producto, pk=pk)
    imagen = ImagenProducto.objects.filter(id_producto=producto).first()

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            image = form.cleaned_data.get('image')
            if image:
                if imagen:
                    imagen.url_imagen = image
                    imagen.save()
                else:
                    ImagenProducto.objects.create(id_producto=producto, url_imagen=image)
            messages.success(request, 'Producto actualizado correctamente!')
            return redirect('product-dashboard')
        else:
            messages.error(request, 'Por favor, corrija los errores abajo.')
    else:
        initial = {}
        if imagen:
            initial['image'] = imagen.url_imagen
        form = ProductoForm(instance=producto, initial=initial)

    context = {
        'form': form, 
        'producto': producto, 
        'imagen': imagen,
    }
    return render(request, 'products/product_form.html', context)
