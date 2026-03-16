from django.db import models


class Departamento(models.Model):
    id_departamento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['nombre']


class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    id_departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, null=False, related_name='municipios')
    nombre = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.id_departamento.nombre})"

    class Meta:
        ordering = ['id_departamento__nombre', 'nombre']
        unique_together = [['id_departamento', 'nombre']]


class Productor(models.Model):
    id_productor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    imagen = models.ImageField(upload_to='productores_imagenes/', null=True, blank=True)

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