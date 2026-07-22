from django.conf import settings

from recognition.services.embedding_cache import EmbeddingCache
from recognition.services.embedding_utils import best_match


class FaceRecognitionService:
    def __init__(self, threshold=None):
        self.threshold = threshold or float(
            getattr(settings, "RECOGNITION_SIMILARITY_THRESHOLD", 0.65)
        )

    def classify(self, embedding):
        residents = EmbeddingCache.get_residents()
        visitors = EmbeddingCache.get_visitors()

        res_match, res_score = best_match(embedding, residents)
        if res_match and res_score >= self.threshold:
            return "RESIDENT", res_match, res_score

        vis_match, vis_score = best_match(embedding, visitors)
        if vis_match and vis_score >= self.threshold:
            return "VISITOR", vis_match, vis_score

        return "UNKNOWN", None, max(res_score, vis_score)
