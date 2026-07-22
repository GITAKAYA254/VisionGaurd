import base64
import uuid
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone

from visitors.models import Visitor
from recognition.services.embedding_utils import cosine_similarity, best_match


class VisitorTrackingService:
    def __init__(self, threshold=0.65):
        self.threshold = threshold

    def find_or_create(self, embedding, snapshot_b64=None, associated_resident=None):
        visitors = list(
            Visitor.objects.exclude(face_embedding=[]).values("id", "visitor_uuid", "face_embedding", "visit_count")
        )
        entries = [
            {
                "id": str(v["id"]),
                "uuid": str(v["visitor_uuid"]),
                "embedding": v["face_embedding"],
                "visit_count": v["visit_count"],
            }
            for v in visitors
        ]
        match, score = best_match(embedding, entries)

        if match and score >= self.threshold:
            visitor = Visitor.objects.get(pk=match["id"])
            visitor.last_seen = timezone.now()
            visitor.visit_count += 1
            visitor.is_known = True
            if associated_resident:
                visitor.associated_resident = associated_resident
            if snapshot_b64:
                self._save_snapshot(visitor, snapshot_b64)
            visitor.save()
            return visitor, False, score

        visitor = Visitor(
            face_embedding=embedding,
            is_known=False,
            visit_count=1,
            associated_resident=associated_resident,
        )
        if snapshot_b64:
            self._save_snapshot(visitor, snapshot_b64)
        visitor.save()
        return visitor, True, score

    @staticmethod
    def _save_snapshot(visitor, snapshot_b64):
        data = base64.b64decode(snapshot_b64)
        name = f"visitor_{visitor.visitor_uuid or uuid.uuid4()}.jpg"
        visitor.snapshot.save(name, ContentFile(data), save=False)
