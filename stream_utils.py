import sys
import time
import cv2


def parse_stream_source(stream_url):
    try:
        return int(stream_url)
    except (ValueError, TypeError):
        return stream_url


def _warmup_capture(cap, frames=5):
    for _ in range(frames):
        cap.read()
        time.sleep(0.05)


def open_video_capture(stream_url):
    """Open a camera stream. On Windows, try multiple backends for USB webcams."""
    source = parse_stream_source(stream_url)

    if sys.platform == "win32" and isinstance(source, int):
        backends = (cv2.CAP_DSHOW, cv2.CAP_MSMF)
        for backend in backends:
            cap = cv2.VideoCapture(source, backend)
            if cap.isOpened():
                _warmup_capture(cap)
                return cap
            cap.release()

    cap = cv2.VideoCapture(source)
    if cap.isOpened():
        _warmup_capture(cap)
    return cap
