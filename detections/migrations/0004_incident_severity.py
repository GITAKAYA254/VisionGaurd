# Generated manually for Phase 3 Sprint 3.1.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('detections', '0003_delete_visitor'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='severity',
            field=models.CharField(
                choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')],
                default='LOW',
                max_length=10,
            ),
        ),
    ]
