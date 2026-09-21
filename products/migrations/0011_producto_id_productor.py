# Vínculo producto → productor. Es lo que permite cobrar un envío por productor en vez de
# uno por municipio de origen.
#
# Queda `null=True`: hay productos vivos (y soft-deleted, y en revisión) sin productor, y
# volverlo NOT NULL aquí abortaría la migración en producción. La obligatoriedad vive en
# el formulario del dashboard, en el admin y en la cotización (422 producto_sin_productor).
#
# `PROTECT`: borrar un productor con productos debe fallar. Con `SET_NULL` los productos
# quedarían sin origen y dejarían de cotizarse sin que nadie se entere.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_sincroniza_campos_sin_migrar'),
        ('productores', '0004_alter_productor_table'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='id_productor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='productos',
                to='productores.productor',
                help_text=(
                    'Quien despacha. Define el origen del envío y agrupa los fletes del '
                    'pedido. Sin él el producto no se puede cotizar.'
                ),
                verbose_name='Productor',
            ),
        ),
        migrations.AlterField(
            model_name='producto',
            name='id_municipio',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='productos',
                to='locations.municipio',
                help_text='Vacío: se despacha desde el municipio del productor.',
                verbose_name='Municipio de origen (override)',
            ),
        ),
    ]
