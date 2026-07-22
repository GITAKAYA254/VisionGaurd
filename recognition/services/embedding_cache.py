from residents.models import Resident
from visitors.models import Visitor


class EmbeddingCache:
    @staticmethod
    def get_residents():
        return [
            {
                "id": str(r.id),
                "name": r.full_name,
                "embedding": r.face_embedding,
                "type": "RESIDENT",
            }
            for r in Resident.objects.filter(
                is_active=True,
                enrollment_status=Resident.ENROLLMENT_ENROLLED,
            ).exclude(face_embedding=[])
        ]

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
