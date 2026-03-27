import json
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from locations.models import Departamento, Municipio


class Command(BaseCommand):
    help = "Seed Departamento and Municipio tables from api-colombia.com"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing Departamento and Municipio data before seeding.",
        )

    def _fetch_json(self, endpoint):
        url = f"{settings.API_BASE}/{endpoint}"
        self.stdout.write(f"Fetching {url} ...")
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def handle(self, *args, **options):
        if options["clear"]:
            with transaction.atomic():
                mun_deleted, _ = Municipio.objects.all().delete()
                dep_deleted, _ = Departamento.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {dep_deleted} departamentos and "
                    f"{mun_deleted} municipios."
                )
            )

        departments = self._fetch_json("Department")
        cities = self._fetch_json("City")

        dep_created = 0
        mun_created = 0
        api_id_to_dep = {}

        with transaction.atomic():
            for dep in departments:
                obj, created = Departamento.objects.get_or_create(nombre=dep["name"])
                api_id_to_dep[dep["id"]] = obj
                if created:
                    dep_created += 1

            for city in cities:
                dept_instance = api_id_to_dep.get(city["departmentId"])
                if dept_instance is None:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipping city '{city['name']}': "
                            f"departmentId {city['departmentId']} not found"
                        )
                    )
                    continue
                _, created = Municipio.objects.get_or_create(
                    id_departamento=dept_instance,
                    nombre=city["name"],
                )
                if created:
                    mun_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {dep_created} departamentos and "
                f"{mun_created} municipios created."
            )
        )
