import os
import cv2
from ultralytics import YOLO

from .config import (
    YOLO_CLASS_IDS,
    PERSON_CLASS_IDS,
    VEHICLE_CLASS_IDS,
    CONFIDENCE_THRESHOLD,
    INFERENCE_IMGSZ,
)


class DetectionEngine:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.model = None

    def load(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(project_root, "models", "yolov8n.pt")
        print(f"Loading YOLO model for camera {self.camera_id}...")
        self.model = YOLO(model_path)

    def infer(self, frame):
        if self.model is None:
            self.load()
        return self.model.track(
            frame,
            classes=YOLO_CLASS_IDS,
            verbose=False,
            imgsz=INFERENCE_IMGSZ,
            persist=True,
        )

    @staticmethod
    def class_name(results, cls_id):
        names = results[0].names
        return names[int(cls_id)] if names else str(cls_id)

    @staticmethod
    def annotate_frame(frame, results, identity_labels=None):
        annotated = frame.copy()
        if not results or len(results) == 0:
            return annotated

        identity_labels = identity_labels or {}
        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf < CONFIDENCE_THRESHOLD:
                continue

            cls = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            label = None
            if hasattr(box, "id") and box.id is not None:
                track_id = int(box.id[0].item())
                label = identity_labels.get(track_id)
            
            if not label:
                label = DetectionEngine.class_name(results, cls)
                if hasattr(box, "id") and box.id is not None:
                    track_id = int(box.id[0].item())
                    label = f"{label} #{track_id}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        return annotated

    @staticmethod
    def count_detections(results):
        people_count = 0
        vehicle_count = 0
        detected_names = []
        person_boxes = []

        if not results or len(results) == 0:
            return people_count, vehicle_count, detected_names, person_boxes

        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf < CONFIDENCE_THRESHOLD:
                continue

            cls = int(box.cls[0])
            name = DetectionEngine.class_name(results, cls)
            detected_names.append(name)

            if cls in PERSON_CLASS_IDS:
                people_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                track_id = int(box.id[0].item()) if (hasattr(box, "id") and box.id is not None) else None
                person_boxes.append((track_id, (x1, y1, x2, y2)))
            elif cls in VEHICLE_CLASS_IDS:
                vehicle_count += 1

        return people_count, vehicle_count, detected_names, person_boxes


def crop_frame(frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2].copy()
