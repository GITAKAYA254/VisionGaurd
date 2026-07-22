from django.test import SimpleTestCase

from vision_engine.behaviour import (
    BehaviourCooldown,
    TrackHistory,
    point_in_polygon,
    restricted_zones_from_environment,
)


class TrackHistoryTests(SimpleTestCase):
    def test_creates_bounded_track_history_and_dwell_time(self):
        history = TrackHistory(movement_radius=10, max_positions=2, cleanup_timeout=30)
        state = history.update(7, (0, 0, 10, 10), now=100)
        state = history.update(7, (2, 2, 12, 12), now=115)
        state = history.update(7, (3, 3, 13, 13), now=120)

        self.assertEqual(state.track_id, 7)
        self.assertEqual(state.first_seen, 100)
        self.assertEqual(state.last_seen, 120)
        self.assertEqual(state.dwell_time, 20)
        self.assertEqual(len(state.recent_positions), 2)

    def test_movement_resets_current_dwell_interval(self):
        history = TrackHistory(movement_radius=10, max_positions=5, cleanup_timeout=30)
        history.update(7, (0, 0, 10, 10), now=100)
        state = history.update(7, (30, 0, 40, 10), now=115)

        self.assertEqual(state.first_seen, 100)
        self.assertEqual(state.dwell_time, 0)

    def test_expired_tracks_are_cleaned_up(self):
        history = TrackHistory(movement_radius=10, max_positions=5, cleanup_timeout=30)
        history.update(7, (0, 0, 10, 10), now=100)

        self.assertEqual(history.cleanup(now=131), [7])
        self.assertEqual(history.tracks, {})


class BehaviourGeometryTests(SimpleTestCase):
    def test_loitering_condition_and_cooldown(self):
        history = TrackHistory(movement_radius=10, max_positions=5, cleanup_timeout=30)
        history.update(7, (0, 0, 10, 10), now=100)
        state = history.update(7, (2, 2, 12, 12), now=130)
        cooldown = BehaviourCooldown(seconds=60)

        self.assertGreaterEqual(state.dwell_time, 30)
        self.assertTrue(cooldown.ready("loitering:7", now=130))
        self.assertFalse(cooldown.ready("loitering:7", now=131))
        self.assertTrue(cooldown.ready("loitering:7", now=190))

    def test_restricted_zone_point_in_polygon_and_configuration(self):
        polygon = [(0, 0), (20, 0), (20, 20), (0, 20)]
        zones = restricted_zones_from_environment(
            '{"1": [{"name": "Server room", "points": [[0, 0], [20, 0], [20, 20], [0, 20]]}]}'
        )

        self.assertTrue(point_in_polygon((10, 10), polygon))
        self.assertTrue(point_in_polygon((0, 10), polygon))
        self.assertFalse(point_in_polygon((25, 10), polygon))
        self.assertEqual(zones["1"][0]["name"], "Server room")
