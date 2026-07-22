from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Resident
from .forms import ResidentForm
from .services.face_enrollment import FaceEnrollmentService


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
