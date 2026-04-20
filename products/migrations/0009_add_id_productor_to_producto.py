import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0008_remove_municipio_id_departamento_and_more"),
        ("producers", "0002_remove_municipio_id_departamento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="id_productor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="productos",
                to="producers.productor",
                verbose_name="Productor",
            ),
        ),
    ]
