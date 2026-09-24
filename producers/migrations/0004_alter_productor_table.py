from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("productores", "0003_productor_telefono_correo"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="productor",
            table="producers_productor",
        ),
    ]
