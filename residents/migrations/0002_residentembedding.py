# Generated migration for ResidentEmbedding model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('residents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResidentEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding', models.JSONField(blank=True, default=list)),
                ('quality_score', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('resident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='embeddings', to='residents.resident')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='residentembedding',
            index=models.Index(fields=['resident', 'is_active'], name='residents_r_residen_idx'),
        ),
    ]
