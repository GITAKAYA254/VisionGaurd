import cv2
import threading
import time

from stream_utils import open_video_capture
from .api_client import AsyncAPIClient
from .config import (
    DETECTION_FRAME_SKIP,
    RECOGNITION_FRAME_SKIP,
    LOG_FRAME_SKIP,
    STATS_FRAME_SKIP,
    JPEG_QUALITY,
    STREAM_FPS_SLEEP,
    CONFIDENCE_THRESHOLD,
    RECOGNITION_CACHE_TIMEOUT,
    RECOGNITION_RETRY_INTERVAL,
    TRACK_CLEANUP_TIMEOUT,
)
from .detection import DetectionEngine, crop_frame
from . import mjpeg_server
from .recognition import (
    generate_embedding,
    match_embedding,
    fetch_embeddings_from_api,
    encode_snapshot_b64,
)


BLACK_FRAME_MEAN_THRESHOLD = 5.0
BLACK_FRAME_RECONNECT_COUNT = 30


class VisionGuardEngine:
    def __init__(self, camera_id, stream_url, api_url, api_token=None):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.api_url = api_url
        base_url = api_url.split("/detections/")[0]
        self.live_stats_url = f"{base_url}/detections/api/live-stats/"
        self.recognition_url = f"{base_url}/recognition/api/events/"
        self.embeddings_url = base_url
        self.api_token = api_token

        self._running = True
        self._latest_frame = None
        self._annotated_frame = None
        self._frame_lock = threading.Lock()
        self._frame_count = 0

        # Fine-grained thread safety for recognition caches
        self._state_lock = threading.Lock()
        self._track_identities = {}       # track_id -> dict
        self._track_last_seen = {}        # track_id -> timestamp
        self._active_recognition_tasks = set() # set of track_ids currently running deepface

        self._detector = DetectionEngine(camera_id)
        self._api = AsyncAPIClient(api_token=api_token)
        self._embeddings = {"residents": [], "visitors": []}
        self._embeddings_loaded = False
        self._embeddings_last_refresh = 0
        self._cooldowns = {}

    def _encode_publish(self, frame):
        if frame is None:
            return
        ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if not ok:
            return
        mjpeg_server.publish_frame(self.camera_id, jpeg.tobytes())

    def _capture_loop(self):
        cap = open_video_capture(self.stream_url)
        black_frame_count = 0
        while self._running:
            if not cap.isOpened():
                time.sleep(2)
                cap = open_video_capture(self.stream_url)
                black_frame_count = 0
                continue

            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            if frame.mean() < BLACK_FRAME_MEAN_THRESHOLD:
                black_frame_count += 1
                if black_frame_count >= BLACK_FRAME_RECONNECT_COUNT:
                    print(f"Camera {self.camera_id}: black frames detected, reconnecting video source...")
                    cap.release()
                    with self._frame_lock:
                        self._annotated_frame = None
                    time.sleep(1)
                    cap = open_video_capture(self.stream_url)
                    black_frame_count = 0
                continue
            black_frame_count = 0

            with self._frame_lock:
                self._latest_frame = frame
                self._frame_count += 1

        cap.release()

    def _stream_loop(self):
        while self._running:
            with self._frame_lock:
                frame = self._annotated_frame if self._annotated_frame is not None else self._latest_frame
            self._encode_publish(frame)
            time.sleep(STREAM_FPS_SLEEP)

    def _cleanup_stale_tracks(self, now):
        """Remove tracks from cache that haven't been seen for TRACK_CLEANUP_TIMEOUT seconds."""
        with self._state_lock:
            stale_track_ids = []
            for track_id, last_seen in self._track_last_seen.items():
                if now - last_seen > TRACK_CLEANUP_TIMEOUT:
                    stale_track_ids.append(track_id)
            
            for track_id in stale_track_ids:
                self._track_identities.pop(track_id, None)
                self._track_last_seen.pop(track_id, None)
                self._active_recognition_tasks.discard(track_id)

    def _detection_loop(self):
        last_frame_num = -1
        while self._running:
            time.sleep(0.005)
            with self._frame_lock:
                if self._frame_count == 0 or self._latest_frame is None or self._frame_count == last_frame_num:
                    continue
                frame = self._latest_frame.copy()
                frame_num = self._frame_count
            last_frame_num = frame_num
            if frame_num % DETECTION_FRAME_SKIP != 0:
                continue

            try:
                results = self._detector.infer(frame)
                people, vehicles, names, person_boxes = DetectionEngine.count_detections(results)

                # Keep track of active IDs and copy labels for thread-safe annotating
                now = time.time()
                active_labels = {}
                with self._state_lock:
                    for track_id, _ in person_boxes:
                        if track_id is not None:
                            self._track_last_seen[track_id] = now
                    active_labels = {tid: data["identity"] for tid, data in self._track_identities.items()}

                annotated = DetectionEngine.annotate_frame(frame, results, active_labels)

                with self._frame_lock:
                    self._annotated_frame = annotated

                if frame_num % STATS_FRAME_SKIP == 0:
                    detected_names_to_send = list(active_labels.values())
                    for cls_name in names:
                        if cls_name != "person":
                            detected_names_to_send.append(cls_name)

                    self._api.enqueue(
                        self.live_stats_url,
                        {
                            "camera_id": self.camera_id,
                            "people_count": people,
                            "vehicle_count": vehicles,
                            "detected_names": detected_names_to_send,
                        },
                    )

                if frame_num % LOG_FRAME_SKIP == 0:
                    for box in results[0].boxes:
                        conf = float(box.conf[0])
                        if conf < CONFIDENCE_THRESHOLD:
                            continue
                        cls = int(box.cls[0])
                        class_name = DetectionEngine.class_name(results, cls)
                        if class_name != "person":
                            self._api.enqueue(
                                self.api_url,
                                {
                                    "camera_id": self.camera_id,
                                    "class_name": class_name,
                                    "confidence": conf,
                                },
                            )

                # Determine if any tracked person needs face recognition
                for track_id, bbox in person_boxes:
                    if track_id is None:
                        continue

                    should_recognize = False
                    with self._state_lock:
                        if track_id in self._active_recognition_tasks:
                            continue

                        cached = self._track_identities.get(track_id)
                        if cached is None:
                            should_recognize = True
                        else:
                            elapsed = now - cached["last_recognized"]
                            if elapsed >= RECOGNITION_CACHE_TIMEOUT:
                                should_recognize = True
                            elif (cached["person_type"] == "UNKNOWN" or cached["confidence"] < CONFIDENCE_THRESHOLD) and elapsed >= RECOGNITION_RETRY_INTERVAL:
                                should_recognize = True

                    if should_recognize:
                        with self._state_lock:
                            self._active_recognition_tasks.add(track_id)

                        x1, y1, x2, y2 = bbox
                        crop = crop_frame(frame, x1, y1, x2, y2)
                        if crop is not None:
                            threading.Thread(
                                target=self._recognize_persons,
                                args=(crop, track_id),
                                daemon=True,
                            ).start()
                        else:
                            with self._state_lock:
                                self._active_recognition_tasks.discard(track_id)

                if frame_num % 30 == 0:
                    self._cleanup_stale_tracks(now)

            except Exception as e:
                print(f"Detection error camera {self.camera_id}: {e}")

    def _refresh_embeddings_if_needed(self):
        now = time.time()
        if not self._embeddings_loaded or now - self._embeddings_last_refresh > 60:
            self._embeddings = fetch_embeddings_from_api(self.embeddings_url, self.api_token)
            self._embeddings_loaded = True
            self._embeddings_last_refresh = now

    def _cooldown_active(self, key):
        now = time.time()
        last = self._cooldowns.get(key, 0)
        from .config import RECOGNITION_COOLDOWN_SECONDS
        if now - last < RECOGNITION_COOLDOWN_SECONDS:
            return True
        self._cooldowns[key] = now
        return False

    def _recognize_persons(self, crop, track_id):
        try:
            self._refresh_embeddings_if_needed()
            embedding = generate_embedding(crop)

            person_type = "UNKNOWN"
            match = None
            confidence = 0.0

            if embedding is not None:
                person_type, match, confidence = match_embedding(
                    embedding,
                    self._embeddings.get("residents", []),
                    self._embeddings.get("visitors", []),
                )

            now = time.time()
            label = "Unknown"

            if person_type == "RESIDENT" and match:
                cooldown_key = f"resident:{match['id']}"
                label = match.get("name", "resident")
                with self._state_lock:
                    cached = self._track_identities.get(track_id, {})
                    cached.update({
                        "identity": label,
                        "person_type": "RESIDENT",
                        "confidence": confidence,
                        "last_recognized": now,
                    })
                    self._track_identities[track_id] = cached

                if not self._cooldown_active(cooldown_key):
                    self._api.enqueue(
                        self.recognition_url,
                        {
                            "camera_id": self.camera_id,
                            "person_type": "RESIDENT",
                            "resident_id": match["id"],
                            "confidence": confidence,
                            "cooldown_key": cooldown_key,
                            "snapshot_b64": encode_snapshot_b64(crop),
                        },
                    )
            elif person_type == "VISITOR" and match:
                cooldown_key = f"visitor:{match['id']}"
                label = match.get("name", "visitor")
                with self._state_lock:
                    cached = self._track_identities.get(track_id, {})
                    cached.update({
                        "identity": label,
                        "person_type": "VISITOR",
                        "confidence": confidence,
                        "last_recognized": now,
                    })
                    self._track_identities[track_id] = cached

                if not self._cooldown_active(cooldown_key):
                    self._api.enqueue(
                        self.recognition_url,
                        {
                            "camera_id": self.camera_id,
                            "person_type": "VISITOR",
                            "visitor_id": match["id"],
                            "confidence": confidence,
                            "cooldown_key": cooldown_key,
                            "snapshot_b64": encode_snapshot_b64(crop),
                        },
                    )
            else:
                cooldown_key = f"unknown:{track_id}"
                label = f"Unknown #{track_id}"
                with self._state_lock:
                    cached = self._track_identities.get(track_id, {})
                    cached.update({
                        "identity": label,
                        "person_type": "UNKNOWN",
                        "confidence": confidence,
                        "last_recognized": now,
                    })
                    self._track_identities[track_id] = cached

                if not self._cooldown_active(cooldown_key):
                    self._api.enqueue(
                        self.recognition_url,
                        {
                            "camera_id": self.camera_id,
                            "person_type": "UNKNOWN",
                            "confidence": confidence,
                            "cooldown_key": cooldown_key,
                            "embedding": embedding if embedding is not None else [],
                            "snapshot_b64": encode_snapshot_b64(crop),
                        },
                    )
        except Exception as e:
            print(f"Error in recognition thread for camera {self.camera_id}, track {track_id}: {e}")
        finally:
            with self._state_lock:
                self._active_recognition_tasks.discard(track_id)

    def run(self):
        mjpeg_server.start_server_if_not_running()
        print(f"Starting Vision Engine for Camera {self.camera_id} (threaded pipeline)...")

        threads = [
            threading.Thread(target=self._capture_loop, daemon=True),
            threading.Thread(target=self._stream_loop, daemon=True),
            threading.Thread(target=self._detection_loop, daemon=True),
        ]
        for t in threads:
            t.start()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._running = False
            self._api.stop()
