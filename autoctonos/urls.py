from django.urls import include, path
from rest_framework import routers, permissions
from django.contrib import admin
from users import views as users_views
from products import views as products_views
from products import panel as products_panel
from commerce import views as commerce_views
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf.urls.static import static
from django.conf import settings
from products import urls as product_url
from users import urls as user_url
from commerce import urls as commerce_url

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API documentation for the project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@myapi.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=False,
    permission_classes=(permissions.IsAdminUser,),
)

router = routers.DefaultRouter()

admin.site.site_header = "Autóctonos · Administración"
admin.site.site_title = "Autóctonos admin"
admin.site.index_title = "Panel de administración"

urlpatterns = [
    path('api/', include(router.urls)),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path("admin/", admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/productos/', include(product_url)),
    path('api/users/', include(user_url)),
    path('api/commerce/', include(commerce_url)),
    path('dashboard/', products_panel.product_dashboard, name='product-dashboard'),
    path('dashboard/<int:pk>/edit/', products_panel.product_update, name='product-update'),
    path('panel/', products_panel.formulario_productor, name='panel-productor'),
    path('panel/productos/', products_panel.productos_de_productor, name='panel-productos'),
    path('dashboard/export/', products_views.product_export, name='product-export'),
    path('api/productores/', include('producers.urls')),
    path('api/locations/', include('locations.urls')),
    path('api/envios/', include('shipping.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
