from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Resident
from .forms import ResidentForm
from .services.face_enrollment import FaceEnrollmentService
from .services.face_enhancement import FaceEnhancementService


class ResidentListView(LoginRequiredMixin, ListView):
    model = Resident
    template_name = "residents/resident_list.html"
    context_object_name = "residents"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(house_number__icontains=q)
                | Q(phone_number__icontains=q)
            )
        return qs


class ResidentDetailView(LoginRequiredMixin, DetailView):
    model = Resident
    template_name = "residents/resident_detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resident = self.object
        context['embedding_count'] = FaceEnhancementService.get_embedding_count(resident)
        return context


class ResidentCreateView(LoginRequiredMixin, CreateView):
    model = Resident
    form_class = ResidentForm
    template_name = "residents/resident_form.html"
    success_url = reverse_lazy("resident_list")


class ResidentUpdateView(LoginRequiredMixin, UpdateView):
    model = Resident
    form_class = ResidentForm
    template_name = "residents/resident_form.html"
    success_url = reverse_lazy("resident_list")

    def form_valid(self, form):
        if "photo" in form.changed_data:
            form.instance.enrollment_status = Resident.ENROLLMENT_PENDING
            form.instance.enrollment_error = ""
        return super().form_valid(form)


class ResidentDeleteView(LoginRequiredMixin, DeleteView):
    model = Resident
    template_name = "residents/resident_confirm_delete.html"
    success_url = reverse_lazy("resident_list")


@login_required
def resident_dashboard(request):
    residents = Resident.objects.all()
    return ListView.as_view(
        model=Resident,
        template_name="residents/resident_dashboard.html",
        context_object_name="residents",
    )(request)


@login_required
def enhance_face_view(request, pk):
    """Display webcam capture page for enhancing resident face."""
    resident = get_object_or_404(Resident, pk=pk)
    return render(request, 'residents/enhance_face.html', {'resident': resident})


class ReEnrollAPI(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated or request.user.role != "ADMIN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            resident = Resident.objects.get(pk=pk)
        except Resident.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        FaceEnrollmentService.enroll(resident)
        return Response({"status": resident.enrollment_status, "error": resident.enrollment_error})


class EnhanceFaceAPI(APIView):
    """
    API endpoint for enhancing resident face recognition with multiple webcam captures.
    POST /residents/<resident_id>/enhance-face/
    Body: {"images": ["base64_image_1", "base64_image_2", ...]}
    """
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            resident = Resident.objects.get(pk=pk)
        except Resident.DoesNotExist:
            return Response({"error": "Resident not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get base64 images from request
        images = request.data.get("images", [])
        
        if not images:
            return Response(
                {"error": "No images provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(images, list):
            return Response(
                {"error": "Images must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        MAX_IMAGES = 10
        if not all(isinstance(image, str) for image in images):
            return Response(
                {"error": "Each image must be a base64 string"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(images) > MAX_IMAGES:
            return Response(
                {"error": f"Too many images (max {MAX_IMAGES})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the images
        result = FaceEnhancementService.process_webcam_captures(resident, images)
        
        return Response(result, status=status.HTTP_200_OK)
