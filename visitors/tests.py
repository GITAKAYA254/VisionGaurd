from django.test import TestCase
from visitors.models import Visitor
from visitors.services.visitor_tracking import VisitorTrackingService


class VisitorTrackingTests(TestCase):
    def test_creates_new_visitor(self):
        embedding = [0.1] * 512
        visitor, created, score = VisitorTrackingService().find_or_create(embedding)
        self.assertTrue(created)
        self.assertEqual(visitor.visit_count, 1)
        self.assertEqual(len(visitor.face_embedding), 512)

    def test_repeat_visitor_increments_count(self):
        embedding = [0.2] * 512
        tracker = VisitorTrackingService(threshold=0.65)
        v1, created1, _ = tracker.find_or_create(embedding)
        self.assertTrue(created1)
        v2, created2, _ = tracker.find_or_create(embedding)
        self.assertFalse(created2)
        self.assertEqual(v1.id, v2.id)
        v2.refresh_from_db()
        self.assertEqual(v2.visit_count, 2)
        self.assertTrue(v2.is_known)
