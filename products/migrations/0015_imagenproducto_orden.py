from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_categoria_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='imagenproducto',
            name='orden',
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name='Orden',
                help_text='La foto con el número más bajo es la portada del producto en la tienda.',
            ),
        ),
        migrations.AlterModelOptions(
            name='imagenproducto',
            options={
                'ordering': ['orden', 'id_imagen'],
                'verbose_name': 'Imagen de Producto',
                'verbose_name_plural': 'Imágenes de Productos',
            },
        ),
    ]
