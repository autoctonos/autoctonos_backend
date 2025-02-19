from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)
