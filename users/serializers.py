from django.contrib.auth.models import Group
from rest_framework import serializers
from .models import Usuario


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
