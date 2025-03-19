from django.urls import include, path
from .views import UserViewSet, GroupViewSet, UserMeView
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import routers, permissions

router = routers.DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('me/', UserMeView.as_view(), name='user-me'),
]

