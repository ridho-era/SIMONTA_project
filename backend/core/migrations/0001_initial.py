from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HalamanBantuan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("judul", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("ringkasan", models.CharField(blank=True, max_length=300)),
                ("konten", models.TextField()),
                ("urutan", models.PositiveSmallIntegerField(default=0)),
                ("aktif", models.BooleanField(default=True)),
                ("diperbarui_pada", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "halaman bantuan",
                "verbose_name_plural": "halaman bantuan",
                "ordering": ["urutan", "judul", "id"],
            },
        ),
    ]
