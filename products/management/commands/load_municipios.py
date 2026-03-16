import requests
from django.core.management.base import BaseCommand
from products.models import Departamento, Municipio

class Command(BaseCommand):
    help = 'Carga departamentos y municipios desde la API Colombia'

    def handle(self, *args, **kwargs):
        self.stdout.write('Cargando departamentos...')
        response = requests.get('https://api-colombia.com/api/v1/Department')
        departamentos = response.json()

        for dep in departamentos:
            obj, created = Departamento.objects.get_or_create(
                id_departamento=dep['id'],
                defaults={'nombre': dep['name']}
            )
            if created:
                self.stdout.write(f'  + {dep["name"]}')

        self.stdout.write('Cargando municipios...')
        response = requests.get('https://api-colombia.com/api/v1/City')
        municipios = response.json()

        for mun in municipios:
            try:
                departamento = Departamento.objects.get(id_departamento=mun['departmentId'])
                Municipio.objects.get_or_create(
                    id_municipio=mun['id'],
                    defaults={
                        'nombre': mun['name'],
                        'id_departamento': departamento
                    }
                )
            except Departamento.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('✅ Municipios y departamentos cargados'))
