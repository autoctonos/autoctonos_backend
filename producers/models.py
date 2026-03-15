from django.db import models


class Productor(models.Model):
    id_productor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    imagen = models.ImageField(upload_to='productores_imagenes/', null=True, blank=True)
    origen = models.ForeignKey(
        'cities_light.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ciudad de Origen"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)


    class Meta:
        verbose_name = "Productor"
        verbose_name_plural = "Productores"

    def __str__(self):
        return self.nombre