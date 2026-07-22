from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Visitor


class VisitorListView(LoginRequiredMixin, ListView):
    model = Visitor
    template_name = "visitors/visitor_list.html"
    context_object_name = "visitors"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("associated_resident")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(visitor_uuid__icontains=q) | Q(notes__icontains=q))
        return qs


class VisitorDetailView(LoginRequiredMixin, DetailView):
    model = Visitor
    template_name = "visitors/visitor_detail.html"
