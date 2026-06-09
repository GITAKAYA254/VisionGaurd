from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from detections.models import Detection, Incident
from cameras.models import Camera
from django.db.models import Count
from django.utils import timezone

@login_required
def dashboard_index(request):
    total_cameras = Camera.objects.count()
    active_cameras = Camera.objects.filter(is_active=True).count()
    recent_detections = Detection.objects.order_by('-timestamp')[:10]
    active_incidents = Incident.objects.filter(status='OPEN').order_by('-risk_score')
    
    # Stats for today
    today = timezone.now().date()
    detections_today = Detection.objects.filter(timestamp__date=today).count()
    
    context = {
        'total_cameras': total_cameras,
        'active_cameras': active_cameras,
        'recent_detections': recent_detections,
        'active_incidents': active_incidents,
        'detections_today': detections_today,
    }
    return render(request, 'dashboard/index.html', context)

@login_required
def live_monitor(request):
    cameras = Camera.objects.filter(is_active=True)
    return render(request, 'dashboard/monitor.html', {'cameras': cameras})

@login_required
def estate_map(request):
    cameras = Camera.objects.filter(is_active=True)
    cameras_data = [
        {
            'name': c.name,
            'lat': float(c.latitude) if c.latitude else None,
            'lng': float(c.longitude) if c.longitude else None,
            'location': c.location_name,
            'status': c.status
        } for c in cameras
    ]
    return render(request, 'dashboard/map.html', {
        'cameras': cameras,
        'cameras_json': cameras_data
    })
