from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(max_length=50)),
                ("user_id", models.BigIntegerField()),
                ("username", models.CharField(max_length=150)),
                ("detail", models.CharField(blank=True, default="", max_length=300)),
                ("created", models.FloatField()),
            ],
        ),
    ]
