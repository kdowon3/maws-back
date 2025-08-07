# Generated manually for adding tags field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_alter_client_options_client_name_client_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='tags',
            field=models.JSONField(blank=True, default=list, verbose_name='태그'),
        ),
    ]