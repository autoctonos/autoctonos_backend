from django.contrib import admin
from .models import Departamento, Municipio


class HiddenAdmin(admin.ModelAdmin):
    """Registrado para soporte de autocomplete_fields, pero oculto del índice del admin."""

    def get_model_perms(self, request):
        return {}


@admin.register(Departamento)
class DepartamentoAdmin(HiddenAdmin):
    search_fields = ('nombre',)


@admin.register(Municipio)
class MunicipioAdmin(HiddenAdmin):
    search_fields = ('nombre',)
    autocomplete_fields = ('id_departamento',)
