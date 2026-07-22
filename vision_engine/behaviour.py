"""In-memory behaviour helpers used by the vision pipeline.

Track history deliberately stays in the engine process: tracker IDs are
short-lived and are not suitable for persistent database records.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import math
import os
import time


@dataclass
class PersonTrack:
    track_id: int
    first_seen: float
    last_seen: float
    anchor_position: tuple[float, float]
    stationary_since: float
    recent_positions: deque = field(default_factory=deque)

    @property
    def dwell_time(self) -> float:
        """Time spent within the current movement radius."""
        return self.last_seen - self.stationary_since


class TrackHistory:
    """Keeps a bounded, per-person history for a single camera engine."""

    def __init__(self, movement_radius, max_positions, cleanup_timeout):
        self.movement_radius = float(movement_radius)
        self.max_positions = int(max_positions)
        self.cleanup_timeout = float(cleanup_timeout)
        self.tracks = {}

    @staticmethod
    def center(bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def update(self, track_id, bbox, now=None):
        now = time.time() if now is None else now
        position = self.center(bbox)
        state = self.tracks.get(track_id)
        if state is None:
            state = PersonTrack(
                track_id=track_id,
                first_seen=now,
                last_seen=now,
                anchor_position=position,
                stationary_since=now,
                recent_positions=deque(maxlen=self.max_positions),
            )
            self.tracks[track_id] = state
        elif math.dist(position, state.anchor_position) > self.movement_radius:
            # A meaningful move begins a new dwell interval, while retaining
            # first_seen and the bounded recent-position trail.
            state.anchor_position = position
            state.stationary_since = now

        state.last_seen = now
        state.recent_positions.append((position[0], position[1], now))
        return state

    def cleanup(self, now=None):
        now = time.time() if now is None else now
        expired = [
            track_id
            for track_id, state in self.tracks.items()
            if now - state.last_seen > self.cleanup_timeout
        ]
        for track_id in expired:
            del self.tracks[track_id]
        return expired


class BehaviourCooldown:
    """Bounds repeated behaviour events while a person remains in a state."""

    def __init__(self, seconds):
        self.seconds = float(seconds)
        self._last_emitted = {}

    def ready(self, key, now=None):
        now = time.time() if now is None else now
        previous = self._last_emitted.get(key)
        if previous is not None and now - previous < self.seconds:
            return False
        self._last_emitted[key] = now
        return True

    def cleanup(self, now=None):
        now = time.time() if now is None else now
        self._last_emitted = {
            key: emitted_at
            for key, emitted_at in self._last_emitted.items()
            if now - emitted_at <= self.seconds
        }


def point_in_polygon(point, polygon):
    """Return whether a point is inside, or on the edge of, a polygon."""
    x, y = point
    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        x1, y1 = start
        x2, y2 = end
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y):
            intersection_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < intersection_x:
                inside = not inside
    return inside


def restricted_zones_from_environment(raw=None):
    """Load {camera_id: [{name: str, points: [[x, y], ...]}]} safely."""
    raw = os.environ.get("RESTRICTED_ZONES_JSON", "{}") if raw is None else raw
    try:
        configured = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(configured, dict):
        return {}

    zones = {}
    for camera_id, entries in configured.items():
        if not isinstance(entries, list):
            continue
        valid_entries = []
        for entry in entries:
            points = entry.get("points") if isinstance(entry, dict) else None
            if not isinstance(points, list) or len(points) < 3:
                continue
            try:
                normalized = [(float(point[0]), float(point[1])) for point in points]
            except (TypeError, ValueError, IndexError):
                continue
            valid_entries.append({"name": str(entry.get("name", "Restricted zone")), "points": normalized})
        if valid_entries:
            zones[str(camera_id)] = valid_entries
    return zones
