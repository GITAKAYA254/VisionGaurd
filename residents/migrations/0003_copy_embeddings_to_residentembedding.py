# Data migration: Copy existing face_embedding data from Resident to ResidentEmbedding

from django.db import migrations


def copy_embeddings_forward(apps, schema_editor):
    """
    Copy existing Resident.face_embedding to ResidentEmbedding records.
    Creates one ResidentEmbedding per Resident that has an embedding.
    """
    Resident = apps.get_model('residents', 'Resident')
    ResidentEmbedding = apps.get_model('residents', 'ResidentEmbedding')
    
    for resident in Resident.objects.all():
        if resident.face_embedding:  # Only if embedding exists and is not empty
            ResidentEmbedding.objects.create(
                resident=resident,
                embedding=resident.face_embedding,
                quality_score=None,
                is_active=True,
            )


def copy_embeddings_backward(apps, schema_editor):
    """
    Reverse migration: Copy primary (most recent active) ResidentEmbedding back to Resident.
    This preserves data in case of rollback.
    """
    Resident = apps.get_model('residents', 'Resident')
    ResidentEmbedding = apps.get_model('residents', 'ResidentEmbedding')
    
    for resident in Resident.objects.all():
        # Get the most recent active embedding
        latest_embedding = ResidentEmbedding.objects.filter(
            resident=resident,
            is_active=True
        ).order_by('-created_at').first()
        
        if latest_embedding:
            resident.face_embedding = latest_embedding.embedding
            resident.save(update_fields=['face_embedding'])


class Migration(migrations.Migration):

    dependencies = [
        ('residents', '0002_residentembedding'),
    ]

    operations = [
        migrations.RunPython(copy_embeddings_forward, copy_embeddings_backward),
    ]
