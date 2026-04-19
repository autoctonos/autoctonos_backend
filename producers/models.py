from django.db import models
from locations.models import Municipio


class Productor(models.Model):
    id_productor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    imagen = models.ImageField(upload_to='productores_imagenes/', null=True, blank=True)

    telefono = models.CharField(max_length=20, null=False, blank=False, verbose_name="Teléfono")
    correo = models.EmailField(null=True, blank=True, verbose_name="Correo Electrónico")

    id_municipio = models.ForeignKey(
        Municipio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productores',
        verbose_name="Ubicación (Municipio)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'producers_productor'
        verbose_name = "Productor"
        verbose_name_plural = "Productores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def ubicacion_completa(self):
        if self.id_municipio and self.id_municipio.id_departamento:
            return f"{self.id_municipio.nombre}, {self.id_municipio.id_departamento.nombre}"
        elif self.id_municipio:
            return self.id_municipio.nombre
        return ""
