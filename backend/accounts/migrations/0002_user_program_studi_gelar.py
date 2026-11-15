from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("akademik", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gelar",
            field=models.CharField(blank=True, max_length=100, verbose_name="gelar"),
        ),
        migrations.AddField(
            model_name="user",
            name="program_studi",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pengguna",
                to="akademik.programstudi",
                verbose_name="program studi",
            ),
        ),
    ]
