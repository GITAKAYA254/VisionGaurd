from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from .models import Camera
from stream_utils import open_video_capture
import cv2
import logging
import numpy as np
import time
import requests

logger = logging.getLogger(__name__)


class CameraListView(LoginRequiredMixin, ListView):
    model = Camera
    template_name = 'cameras/camera_list.html'
    context_object_name = 'cameras'

class CameraCreateView(LoginRequiredMixin, CreateView):
    model = Camera
    fields = ['name', 'stream_url', 'location_name', 'latitude', 'longitude', 'is_active']
    template_name = 'cameras/camera_form.html'
    success_url = reverse_lazy('camera_list')

class CameraUpdateView(LoginRequiredMixin, UpdateView):
    model = Camera
    fields = ['name', 'stream_url', 'location_name', 'latitude', 'longitude', 'is_active', 'status']
    template_name = 'cameras/camera_form.html'
    success_url = reverse_lazy('camera_list')

class CameraDeleteView(LoginRequiredMixin, DeleteView):
    model = Camera
    template_name = 'cameras/camera_confirm_delete.html'
    success_url = reverse_lazy('camera_list')

def _placeholder_frame(message, detail=""):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, message, (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    if detail:
        cv2.putText(frame, detail, (40, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()


def _yield_mjpeg_frame(frame_bytes):
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
    )


def _relay_engine_stream(camera_id):
    engine_url = f"http://127.0.0.1:8050/feed/{camera_id}"
    # Connect quickly, but do not time out between MJPEG chunks while YOLO warms up.
    response = requests.get(engine_url, stream=True, timeout=(3, None))
    if response.status_code != 200:
        return

    logger.info("Camera %s: relaying stream from detection engine", camera_id)
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            yield chunk


def gen_frames(camera_id, stream_url):
    last_engine_log = 0.0
    last_capture_log = 0.0

    while True:
        relayed = False
        try:
            for chunk in _relay_engine_stream(camera_id):
                relayed = True
                yield chunk
        except Exception:
            now = time.time()
            if now - last_engine_log > 30:
                logger.warning(
                    "Camera %s: detection engine not running on port 8050. "
                    "Start it with: python manage.py run_vanguard",
                    camera_id,
                )
                last_engine_log = now

        if relayed:
            logger.info("Camera %s: detection engine stream ended, reconnecting", camera_id)
            time.sleep(1)
            continue

        cap = open_video_capture(stream_url)
        if not cap.isOpened():
            now = time.time()
            if now - last_capture_log > 30:
                logger.warning("Camera %s: could not open video source %s", camera_id, stream_url)
                last_capture_log = now
            if str(stream_url) == "0":
                detail = "Close other apps using the webcam"
            else:
                detail = f"Source: {stream_url}"
            frame_bytes = _placeholder_frame("Camera Stream Unavailable", detail)
            yield _yield_mjpeg_frame(frame_bytes)
            time.sleep(2)
            continue

        logger.info("Camera %s: using direct camera capture", camera_id)
        frames_before_retry = 0
        while True:
            success, frame = cap.read()
            if not success:
                frame_bytes = _placeholder_frame("Stream Lost/Interrupted")
                yield _yield_mjpeg_frame(frame_bytes)
                time.sleep(2)
                break

            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue
            yield _yield_mjpeg_frame(buffer.tobytes())

            frames_before_retry += 1
            if frames_before_retry >= 300:
                cap.release()
                break

        if cap.isOpened():
            cap.release()

@login_required
def camera_feed(request, camera_id):
    camera = get_object_or_404(Camera, id=camera_id)
    return StreamingHttpResponse(
        gen_frames(camera.id, camera.stream_url),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )

