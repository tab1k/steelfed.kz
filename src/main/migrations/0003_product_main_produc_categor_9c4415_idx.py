# Generated by Django 5.1.6 on 2025-04-08 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_service_description_service_slug'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='main_produc_categor_9c4415_idx'),
        ),
    ]
