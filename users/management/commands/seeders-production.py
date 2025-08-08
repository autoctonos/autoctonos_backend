from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Categoria

class Command(BaseCommand):
    help = "Carga categorías y subcategorías producción"

  def handle(self, *args, **kwargs):
        self.create_categorias()
        self.stdout.write(
            self.style.SUCCESS("Datos de producción cargados")
        )

    def create_categorias(self):
        categorias = [
            "QUESOS",
            "BEBIDAS",
            "AMASIJOS",
            "CAFÉ",
            "TEJIDOS",
            "COLACIONES",
            "CESTERIA",
            "ARTESANIAS",
            "EMBUTIDOS Y ENCURTIDOS",
            "SALUD",
            "MUEBLES"
        ]
        for nombre in categorias:
            Categoria.objects.get_or_create(nombre=nombre)
        self.stdout.write(self.style.SUCCESS("11 categorías creadas"))

