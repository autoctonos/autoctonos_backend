"""
URL configuration for autoctonos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from rest_framework import routers, permissions
from django.contrib import admin
from users import views as users_views
from products import views as products_views
from commerce import views as commerce_views
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API documentation for the project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@myapi.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'users', users_views.UserViewSet)
router.register(r'groups', users_views.GroupViewSet)

router.register(r'productos', products_views.ProductoViewSet)
router.register(r'categorias', products_views.CategoriaViewSet)
router.register(r'posts', products_views.PostViewSet)

router.register(r'pedidos', commerce_views.PedidoViewSet)
router.register(r'detalle_pedidos', commerce_views.DetallePedidoViewSet)
router.register(r'pagos', commerce_views.PagoViewSet)
router.register(r'envios', commerce_views.EnvioViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path("admin/", admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]