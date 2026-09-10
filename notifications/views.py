from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.select_related("camera").all()
    unread_count = notifications.filter(is_read=False).count()

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@login_required
def notification_detail(request, pk):
    notification = get_object_or_404(Notification.objects.select_related("camera"), pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return render(
        request,
        "notifications/notification_detail.html",
        {"notification": notification},
    )


@login_required
def notification_view_live(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return redirect(notification.live_url)


@login_required
def live_notifications_api(request):
    since_id = request.GET.get("since_id", 0)
    try:
        since_id = int(since_id)
    except ValueError:
        since_id = 0

    notifications = (
        Notification.objects.select_related("camera")
        .filter(id__gt=since_id, is_read=False)
        .order_by("id")[:20]
    )

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "camera_name": n.camera.name if n.camera else "Front Door",
            "camera_id": n.camera_id,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "time_ago": n.created_at.strftime("%H:%M"),
            "live_url": f"/notifications/{n.id}/live/",
            "detail_url": f"/notifications/{n.id}/",
            "snapshot_url": n.snapshot.url if n.snapshot else None,
        }
        for n in notifications
    ]

    return JsonResponse({"notifications": data})


@login_required
@require_POST
def mark_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    notification.is_read = True
    notification.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success", "id": pk})
    return redirect("notification_list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    return redirect("notification_list")
