from django.core.management.base import BaseCommand
from django.conf import settings
from cameras.models import Camera
from vision_engine import VisionGuardEngine
import threading
import time

class Command(BaseCommand):
    help = 'Runs the Detection Engine for all active cameras'

    def handle(self, *args, **options):
        cameras = Camera.objects.filter(is_active=True)
        if not cameras.exists():
            self.stdout.write(self.style.WARNING("No active cameras found in database."))
            return

        threads = []
        api_url = f"{settings.DJANGO_API_URL.rstrip('/')}/detections/api/log/"
        api_token = settings.VISION_GUARD_ENGINE_TOKEN

        for camera in cameras:
            self.stdout.write(self.style.SUCCESS(f"Starting engine for {camera.name}..."))
            engine = VisionGuardEngine(camera.id, camera.stream_url, api_url, api_token=api_token)
            
            # For Phase 1 we might just run one for testing or use threads
            t = threading.Thread(target=engine.run)
            t.daemon = True
            t.start()
            threads.append(t)

        self.stdout.write(self.style.SUCCESS(f"Running {len(threads)} detection engines. Press Ctrl+C to stop."))
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopping engines..."))
