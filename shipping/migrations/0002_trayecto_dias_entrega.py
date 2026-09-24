# Tiempos de entrega por trayecto (hoja «Convenciones» del tarifario).
#
# Los campos entran con `default=1` sólo para poder poblar las filas existentes, y
# `preserve_default=False` los deja sin default en el modelo: así un `Trayecto` creado sin
# días falla ruidosamente en vez de mentir con 1-1. Los valores reales los pone la
# migración de datos siguiente.

from decimal import Decimal

import django.core.validators
import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trayecto',
            name='dias_entrega_min',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Hoja «Convenciones» del tarifario. Se resuelve con el trayecto aplicado.',
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name='Días hábiles (mínimo)',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trayecto',
            name='dias_entrega_max',
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name='Días hábiles (máximo)',
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='trayecto',
            name='cobrar_kilo_adicional_en_1kg',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'OBSOLETO: el tarifario vigente usa `SI(peso>=1; peso-1; peso)`, que nunca '
                    'cobra adicional en 1 kg. El cálculo ya no lo lee; la columna se elimina en '
                    'el próximo release.'
                ),
                verbose_name='Cobrar kilo adicional en envíos de 1 kg',
            ),
        ),
        # Sólo metadatos: el cálculo deja de leer `cubre_sobreflete` en este release y la
        # columna se elimina en el siguiente.
        migrations.AlterField(
            model_name='promocionenvio',
            name='cubre_sobreflete',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'OBSOLETO: el sobreflete es la garantía del producto y siempre se cobra. '
                    'El cálculo ya no lo lee; la columna se elimina en el próximo release.'
                ),
                verbose_name='Cubre el sobreflete',
            ),
        ),
        migrations.AlterField(
            model_name='promocionenvio',
            name='umbral_subtotal',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('200000.00'),
                help_text='Subtotal de productos a partir del cual se cubre el flete.',
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                verbose_name='Umbral de subtotal',
            ),
        ),
        migrations.AddConstraint(
            model_name='trayecto',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('dias_entrega_max__gte', django.db.models.expressions.F('dias_entrega_min'))
                ),
                name='trayecto_dias_entrega_coherentes',
            ),
        ),
    ]
