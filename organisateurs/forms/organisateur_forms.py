from django import forms
from django.utils.translation import gettext_lazy as _
from organisateurs.models import Organisateur

class OrganisateurForm(forms.ModelForm):
    """Formulaire pour la création et la modification d'un organisateur."""
    class Meta:
        model = Organisateur
        fields = ['user']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'})
        } 