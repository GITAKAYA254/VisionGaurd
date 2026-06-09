import cv2
import requests
import time
import os
from ultralytics import YOLO
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from stream_utils import open_video_capture

YOLO_CLASS_IDS = [0, 2, 5, 7]  # person, car, bus, truck
PERSON_CLASS_IDS = {0}
VEHICLE_CLASS_IDS = {2, 5, 7}
CONFIDENCE_THRESHOLD = 0.5

latest_frames = {}
frame_lock = threading.Lock()
_server_started = False
_server_lock = threading.Lock()


class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_frames
        parts = self.path.split("/")
        if len(parts) >= 3 and parts[1] == "feed":
            try:
                camera_id = int(parts[2])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()

            try:
                while True:
                    with frame_lock:
                        frame_bytes = latest_frames.get(camera_id)
                    if frame_bytes is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame_bytes)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.04)
            except (ConnectionResetError, BrokenPipeError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_http_server():
    try:
        server = HTTPServer(("127.0.0.1", 8050), MJPEGHandler)
        print("MJPEG Stream Server running on http://127.0.0.1:8050/feed/<camera_id>")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start MJPEG Stream Server: {e}")


def start_server_if_not_running():
    global _server_started
    with _server_lock:
        if not _server_started:
            t = threading.Thread(target=start_http_server, daemon=True)
            t.start()
            _server_started = True


def _class_name(results, cls_id):
    names = results[0].names
    return names[int(cls_id)] if names else str(cls_id)


def _annotate_frame(frame, results):
    annotated = frame.copy()
    if not results or len(results) == 0:
        return annotated

    for box in results[0].boxes:
        conf = float(box.conf[0])
        if conf < CONFIDENCE_THRESHOLD:
            continue

        cls = int(box.cls[0])
        name = _class_name(results, cls)
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label_y = max(y1 - 10, 20)
        cv2.putText(
            annotated,
            name,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    return annotated


def _count_detections(results):
    people_count = 0
    vehicle_count = 0
    detected_names = []

    if not results or len(results) == 0:
        return people_count, vehicle_count, detected_names

    for box in results[0].boxes:
        conf = float(box.conf[0])
        if conf < CONFIDENCE_THRESHOLD:
            continue

        cls = int(box.cls[0])
        name = _class_name(results, cls)
        detected_names.append(name)

        if cls in PERSON_CLASS_IDS:
            people_count += 1
        elif cls in VEHICLE_CLASS_IDS:
            vehicle_count += 1

    return people_count, vehicle_count, detected_names


class VisionGuardEngine:
    def __init__(self, camera_id, stream_url, api_url, api_token=None):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.api_url = api_url
        self.live_stats_url = api_url.replace("/api/log/", "/api/live-stats/")
        self.api_token = api_token
        self.model = None
        self.cap = open_video_capture(stream_url)
        self.frame_skip = 5
        self.frame_count = 0
        self.stats_skip = 2

    def _load_model(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(project_root, "models", "yolov8n.pt")
        print(f"Loading YOLO model for camera {self.camera_id}...")
        self.model = YOLO(model_path)

    def _publish_frame(self, frame):
        _, jpeg = cv2.imencode(".jpg", frame)
        global latest_frames
        with frame_lock:
            latest_frames[self.camera_id] = jpeg.tobytes()

    def _api_headers(self):
        headers = {}
        if self.api_token:
            headers["X-Engine-Token"] = self.api_token
        return headers

    def update_live_stats(self, people_count, vehicle_count, detected_names):
        data = {
            "camera_id": self.camera_id,
            "people_count": people_count,
            "vehicle_count": vehicle_count,
            "detected_names": detected_names,
        }
        try:
            response = requests.post(
                self.live_stats_url,
                json=data,
                headers=self._api_headers(),
                timeout=5,
            )
            if response.status_code != 200:
                print(f"Error updating live stats: {response.text}")
        except Exception as e:
            print(f"Failed to update live stats: {e}")

    def log_detection(self, class_name, confidence):
        data = {
            "camera_id": self.camera_id,
            "class_name": class_name,
            "confidence": confidence,
        }
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=self._api_headers(),
                timeout=5,
            )
            if response.status_code != 200:
                print(f"Error logging detection: {response.text}")
        except Exception as e:
            print(f"Failed to connect to API: {e}")

    def run(self):
        start_server_if_not_running()
        print(f"Starting Detection Engine for Camera {self.camera_id}...")

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame. Reconnecting...")
                time.sleep(5)
                self.cap = open_video_capture(self.stream_url)
                continue

            self.frame_count += 1

            if self.model is None:
                self._publish_frame(frame)
                if self.frame_count == 1:
                    self._load_model()
                continue

            results = self.model(frame, classes=YOLO_CLASS_IDS, verbose=False)
            annotated_frame = _annotate_frame(frame, results)
            self._publish_frame(annotated_frame)

            people_count, vehicle_count, detected_names = _count_detections(results)
            if self.frame_count % self.stats_skip == 0:
                self.update_live_stats(people_count, vehicle_count, detected_names)

            if self.frame_count % self.frame_skip == 0:
                for box in results[0].boxes:
                    conf = float(box.conf[0])
                    if conf < CONFIDENCE_THRESHOLD:
                        continue
                    cls = int(box.cls[0])
                    class_name = _class_name(results, cls)
                    print(f"Detected {class_name}")
                    self.log_detection(class_name, conf)

        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    ENGINE_API_URL = "http://localhost:8000/detections/api/log/"
    ENGINE_API_TOKEN = os.environ.get("VISION_GUARD_ENGINE_TOKEN", "dev-only-change-before-production")

    engine = VisionGuardEngine(
        camera_id=1,
        stream_url=0,
        api_url=ENGINE_API_URL,
        api_token=ENGINE_API_TOKEN,
    )
    engine.run()
