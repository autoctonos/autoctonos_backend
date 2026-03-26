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
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'


class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    id_departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        null=False,
        related_name='municipios'
    )
    nombre = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.id_departamento.nombre})"

    class Meta:
        ordering = ['id_departamento__nombre', 'nombre']
        unique_together = [['id_departamento', 'nombre']]
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'
