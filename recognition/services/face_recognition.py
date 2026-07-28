from django.conf import settings

from recognition.services.embedding_cache import EmbeddingCache
from recognition.services.embedding_utils import best_match


class FaceRecognitionService:
    def __init__(self, threshold=None, resident_threshold=None, visitor_threshold=None):
        base_threshold = threshold or float(
            getattr(settings, "RECOGNITION_SIMILARITY_THRESHOLD", 0.65)
        )
        self.resident_threshold = resident_threshold or base_threshold
        self.visitor_threshold = visitor_threshold or base_threshold

    def classify(self, embedding):
        residents = EmbeddingCache.get_residents()
        visitors = EmbeddingCache.get_visitors()

        res_match, res_score = best_match(embedding, residents)
        if res_match and res_score >= self.resident_threshold:
            return "RESIDENT", res_match, res_score

        vis_match, vis_score = best_match(embedding, visitors)
        if vis_match and vis_score >= self.visitor_threshold:
            return "VISITOR", vis_match, vis_score

        return "UNKNOWN", None, max(res_score, vis_score)
