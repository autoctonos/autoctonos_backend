# Valores reales de la hoja «Convenciones» del tarifario.
#
# `seed_shipping` también los siembra, pero una base de producción no necesariamente lo
# corre: sin esta migración se quedaría con los 1-1 que puso la migración anterior, y el
# checkout prometería un día hábil para un envío especial de 8-10.

from django.db import migrations

DIAS_POR_TRAYECTO = {
    'urbano': (1, 1),
    'zonal': (1, 3),
    'nacional': (1, 4),
    'territorial': (1, 4),
    'especial': (8, 10),
}


def poblar_dias(apps, schema_editor):
    Trayecto = apps.get_model('shipping', 'Trayecto')
    for codigo, (minimo, maximo) in DIAS_POR_TRAYECTO.items():
        Trayecto.objects.filter(codigo=codigo).update(
            dias_entrega_min=minimo, dias_entrega_max=maximo
        )


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0002_trayecto_dias_entrega'),
    ]

    operations = [
        migrations.RunPython(poblar_dias, migrations.RunPython.noop),
    ]
