"""Backward-compatible entry point for the vision engine."""
import os

from vision_engine import VisionGuardEngine

__all__ = ["VisionGuardEngine"]

if __name__ == "__main__":
    DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000")
    ENGINE_API_URL = f"{DJANGO_API_URL.rstrip('/')}/detections/api/log/"
    ENGINE_API_TOKEN = os.environ.get("VISION_GUARD_ENGINE_TOKEN", "dev-only-change-before-production")

    engine = VisionGuardEngine(
        camera_id=1,
        stream_url=0,
        api_url=ENGINE_API_URL,
        api_token=ENGINE_API_TOKEN,
    )
    engine.run()
