# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ('cliente', 'Cliente'),
        ('productor', 'Productor'),
    ]


    second_name = models.CharField(max_length=255, blank=True, null=True)
    second_last_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    tipo_usuario = models.CharField(max_length=20, choices=TIPO_CHOICES, default='cliente')
    nit = models.CharField(max_length=50, blank=True, null=True)

    def clean(self):
        super().clean()


        if self.tipo_usuario == 'productor' and not self.nit:
            raise ValidationError({
                'nit': 'El NIT es obligatorio si el usuario es un Productor.'
            })


        if self.tipo_usuario == 'cliente' and self.nit:

            raise ValidationError({
                'nit': 'Un usuario tipo Cliente no debe tener un NIT asociado. Por favor, borra este campo.'
            })

