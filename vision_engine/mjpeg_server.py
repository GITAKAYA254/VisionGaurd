import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import time

latest_frames = {}
frame_lock = threading.Lock()
_server_started = False
_server_lock = threading.Lock()


class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
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


def publish_frame(camera_id, jpeg_bytes):
    with frame_lock:
        latest_frames[camera_id] = jpeg_bytes


def start_server_if_not_running(host="127.0.0.1", port=8050):
    global _server_started

    def _run():
        try:
            server = ThreadingHTTPServer((host, port), MJPEGHandler)
            print(f"MJPEG Stream Server running on http://{host}:{port}/feed/<camera_id>")
            server.serve_forever()
        except Exception as e:
            print(f"Failed to start MJPEG Stream Server: {e}")

    with _server_lock:
        if not _server_started:
            threading.Thread(target=_run, daemon=True).start()
            _server_started = True
