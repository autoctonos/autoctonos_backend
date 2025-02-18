from django.db import models

ROL = [
    ('cliente', 'Cliente'),
    ('admin', 'Administrador')
]

class Usuario (models.Model):
    id_usuario = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    correo_electronico = models.EmailField(unique=True)
    contraseña = models.CharField(max_length=255)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rol_usuario = models.CharField(max_length=20, choices=ROL, default='cliente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)
    deleted_at = models.DateTimeField(default=None, null=True)
