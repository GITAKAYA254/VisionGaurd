from django.db.models import Count, Prefetch

from residents.models import Resident, ResidentEmbedding
from visitors.models import Visitor


class EmbeddingCache:
    @staticmethod
    def get_residents():
        """
        Load resident embeddings from ResidentEmbedding table.
        Falls back to Resident.face_embedding for backward compatibility.
        Returns one entry per active embedding.
        """
        results = []

        residents = (
            Resident.objects.filter(
                is_active=True,
                enrollment_status=Resident.ENROLLMENT_ENROLLED,
            ).annotate(
                total_embeddings=Count("embeddings"),
            ).prefetch_related(
                Prefetch(
                    "embeddings",
                    queryset=ResidentEmbedding.objects.filter(
                        is_active=True
                    ).order_by("-created_at"),
                )
            )
        )

        for resident in residents:
            # Uses the prefetched data (no extra database queries)
            active_embeddings = list(resident.embeddings.all())

            if active_embeddings:
                # New multi-embedding system
                for embedding_record in active_embeddings:
                    if embedding_record.embedding:
                        results.append(
                            {
                                "id": str(resident.id),
                                "embedding_id": str(embedding_record.id),
                                "name": resident.full_name,
                                "embedding": embedding_record.embedding,
                                "quality_score": embedding_record.quality_score,
                                "type": "RESIDENT",
                            }
                        )
            elif resident.total_embeddings == 0:
                # Only fall back if this resident has never had a
                # ResidentEmbedding row created (i.e. pre-migration).
                if resident.face_embedding:
                    results.append(
                        {
                            "id": str(resident.id),
                            "embedding_id": None,
                            "name": resident.full_name,
                            "embedding": resident.face_embedding,
                            "quality_score": None,
                            "type": "RESIDENT",
                        }
                    )

        return results
                

       

    @staticmethod
    def get_visitors():
        return [
            {
                "id": str(v.id),
                "name": f"Visitor {str(v.visitor_uuid)[:8]}",
                "embedding": v.face_embedding,
                "type": "VISITOR",
            }
            for v in Visitor.objects.exclude(face_embedding=[])
        ]

    @classmethod
    def as_api_payload(cls):
        return {
            "residents": cls.get_residents(),
            "visitors": cls.get_visitors(),
        }