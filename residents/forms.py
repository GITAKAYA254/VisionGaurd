from django import forms
from .models import Resident


class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = ["full_name", "house_number", "phone_number", "photo", "is_active"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary"}),
            "house_number": forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary"}),
            "photo": forms.FileInput(attrs={"class": "form-control bg-dark text-light border-secondary"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
