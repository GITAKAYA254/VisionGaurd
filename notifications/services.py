import base64
import uuid
from django.core.files.base import ContentFile
from .models import Notification


def _save_snapshot_b64(notification, snapshot_b64):
    if not snapshot_b64:
        return
    try:
        data = base64.b64decode(snapshot_b64)
        file_name = f"notif_{notification.id}_{uuid.uuid4().hex[:6]}.jpg"
        notification.snapshot.save(file_name, ContentFile(data), save=True)
    except Exception as e:
        print(f"Failed to save notification snapshot: {e}")


class NotificationService:
    @staticmethod
    def notify_resident(resident_name, camera=None, metadata=None, snapshot_b64=None):
        meta = metadata.copy() if metadata else {}
        meta["event_type"] = "RESIDENT"
        meta["resident_name"] = resident_name
        camera_name = camera.name if camera else "Front Door"

        notification = Notification.objects.create(
            title="Resident Detected",
            message=f"{resident_name} arrived at {camera_name}.",
            severity=Notification.SEVERITY_INFO,
            camera=camera,
            metadata=meta,
        )
        _save_snapshot_b64(notification, snapshot_b64)
        return notification

    @staticmethod
    def notify_unknown(track_id=None, camera=None, metadata=None, snapshot_b64=None):
        meta = metadata.copy() if metadata else {}
        meta["event_type"] = "UNKNOWN"
        if track_id is not None:
            meta["track_id"] = str(track_id)
        camera_name = camera.name if camera else "Front Door"

        # Database deduplication: check for existing unread UNKNOWN notification for same track_id & camera
        if track_id is not None:
            existing = Notification.objects.filter(
                severity=Notification.SEVERITY_WARNING,
                camera=camera,
                is_read=False,
                metadata__track_id=str(track_id),
                metadata__event_type="UNKNOWN",
            ).exists()
            if existing:
                return None

        notification = Notification.objects.create(
            title="Unknown Person Detected",
            message=f"An unknown person has been detected at {camera_name}. Tap View Live to investigate.",
            severity=Notification.SEVERITY_WARNING,
            camera=camera,
            metadata=meta,
        )
        _save_snapshot_b64(notification, snapshot_b64)
        return notification

    @staticmethod
    def notify_loitering(track_id=None, camera=None, metadata=None, snapshot_b64=None, person_type=None):
        meta = metadata.copy() if metadata else {}
        p_type = person_type or meta.get("person_type")

        # EXPLICIT BUSINESS RULE: Residents NEVER generate loitering alerts.
        if p_type == "RESIDENT":
            return None

        meta["event_type"] = "LOITERING"
        if track_id is not None:
            meta["track_id"] = str(track_id)
        camera_name = camera.name if camera else "Front Door"

        # Database deduplication: check for existing unread LOITERING notification for same track_id & camera
        if track_id is not None:
            existing = Notification.objects.filter(
                severity=Notification.SEVERITY_HIGH,
                camera=camera,
                is_read=False,
                metadata__track_id=str(track_id),
                metadata__event_type="LOITERING",
            ).exists()
            if existing:
                return None

        notification = Notification.objects.create(
            title="Suspicious Activity",
            message=f"An unknown person has remained near {camera_name} for more than 2 minutes.",
            severity=Notification.SEVERITY_HIGH,
            camera=camera,
            metadata=meta,
        )
        _save_snapshot_b64(notification, snapshot_b64)
        return notification
