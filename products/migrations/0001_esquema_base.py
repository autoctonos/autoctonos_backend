"""Historia de `products` colapsada: el estado final del esquema, en una sola migración.

Las migraciones 0001-0011 no se pueden replayar sobre una base limpia. `0002_post` y
`0002_producto_presentacion` abren dos ramas que crean `Departamento`, `Municipio`,
`fabricante` e `id_municipio` por duplicado y se juntan en `0007_merge_20260325_0057`;
la segunda rama choca con «relation "products_departamento" already exists». Por eso
`manage.py test` no podía ni construir la base de test.

`replaces` deja las dos rutas funcionando: una base que ya aplicó las 14 migraciones marca
ésta como aplicada y no ejecuta nada; una base limpia ejecuta sólo ésta. Las migraciones
viejas se conservan en el repo y no se tocan.

No incluye la migración de datos de `0008` (`copy_locations_from_products`, que movía
departamentos y municipios de `products` a `locations`): sólo corre en la ruta vieja, y
en una base limpia no hay nada que copiar.
"""

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ('products', '0001_initial'),
        ('products', '0002_producto_presentacion'),
        ('products', '0003_producto_departamento_producto_fabricante_and_more'),
        ('products', '0004_departamento_remove_producto_departamento_and_more'),
        ('products', '0005_producto_es_promocionado'),
        ('products', '0006_producto_porcentaje_descuento'),
        ('products', '0002_post'),
        ('products', '0003_departamento_producto_es_promocionado_and_more'),
        ('products', '0004_producto_cantidad_presentacion'),
        ('products', '0007_merge_20260325_0057'),
        ('products', '0008_remove_municipio_id_departamento_and_more'),
        ('products', '0009_peso_y_cadena_de_frio'),
        ('products', '0010_sincroniza_campos_sin_migrar'),
        ('products', '0011_producto_id_productor'),
    ]

    initial = True

    dependencies = [
        ('locations', '0001_initial'),
        ('productores', '0004_alter_productor_table'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id_categoria', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('requiere_frio', models.BooleanField(default=False, help_text='Default para los productos de la categoría. Cada producto puede sobreescribirlo.', verbose_name='Requiere cadena de frío')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id_producto', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock', models.IntegerField()),
                ('presentacion', models.CharField(choices=[('Lb', 'Libras (Lb)'), ('Kg', 'Kilogramos (Kg)'), ('Un', 'Unidad (Un)'), ('Paq', 'Paquete (Paq x12)'), ('Gr', 'Gramos (Gr)'), ('Oz', 'Onzas (Oz)'), ('Lt', 'Litros (Lt)'), ('Ml', 'Mililitros (Ml)'), ('Dz', 'Docena (Dz)'), ('Bt', 'Botella (Cm3)')], default='Un', max_length=10)),
                ('cantidad_presentacion', models.DecimalField(blank=True, decimal_places=2, help_text='Ej: 200 para 200 g, 1.5 para 1.5 L. Opcional.', max_digits=10, null=True, verbose_name='Cantidad por presentación')),
                ('peso_kg', models.DecimalField(blank=True, decimal_places=3, help_text='Peso real de despacho con empaque. Sin él el producto no se puede cotizar.', max_digits=7, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))], verbose_name='Peso de despacho (kg)')),
                ('requiere_frio_override', models.BooleanField(blank=True, default=None, help_text='Vacío: hereda de la categoría.', null=True, verbose_name='Cadena de frío (override)')),
                ('fabricante', models.CharField(blank=True, max_length=200, null=True)),
                ('es_promocionado', models.BooleanField(default=False, verbose_name='Promocionado')),
                ('porcentaje_descuento', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5, null=True, verbose_name='Porcentaje de Descuento (%)')),
                ('estado', models.CharField(choices=[('aprobado', 'Aprobado'), ('rechazado', 'Rechazado'), ('revisión', 'Revisión')], default='revisión', max_length=10, verbose_name='Estado')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('id_categoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.categoria')),
                ('id_municipio', models.ForeignKey(blank=True, help_text='Vacío: se despacha desde el municipio del productor.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='productos', to='locations.municipio', verbose_name='Municipio de origen (override)')),
                ('id_productor', models.ForeignKey(blank=True, help_text='Quien despacha. Define el origen del envío y agrupa los fletes del pedido. Sin él el producto no se puede cotizar.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='productos', to='productores.productor', verbose_name='Productor')),
            ],
            options={
                'verbose_name': 'Producto',
                'verbose_name_plural': 'Productos',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id_post', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock', models.IntegerField()),
                ('estado', models.CharField(choices=[('aprobado', 'Aprobado'), ('rechazado', 'Rechazado'), ('revisión', 'Revisión')], default='revisión', max_length=10)),
                ('mensaje', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('id_categoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.categoria')),
                ('id_usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('producto', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products.producto')),
            ],
            options={
                'verbose_name': 'Post',
                'verbose_name_plural': 'Posts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ImagenProducto',
            fields=[
                ('id_imagen', models.AutoField(primary_key=True, serialize=False)),
                ('url_imagen', models.ImageField(blank=True, max_length=500, null=True, upload_to='productos_imagenes/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(default=None, null=True)),
                ('id_producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.producto')),
            ],
            options={
                'verbose_name': 'Imagen de Producto',
                'verbose_name_plural': 'Imágenes de Productos',
            },
        ),
    ]
