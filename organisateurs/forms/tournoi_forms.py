from django import forms
from django.utils.translation import gettext_lazy as _
from tournois.models import Tournoi

class TournoiForm(forms.ModelForm):
    """Formulaire pour la création et la modification d'un tournoi."""
    
    TYPE_CHOICES = [
        ('championnat', 'Championnat'),
        ('coupe', 'Coupe'),
        ('amical', 'Tournoi amical')
    ]
    
    FORMAT_CHOICES = [
        ('poules', 'Phases de poules'),
        ('elimination', 'Élimination directe'),
        ('poules_elimination', 'Poules + Élimination directe')
    ]
    
    type = forms.ChoiceField(choices=TYPE_CHOICES, initial='amical')
    format = forms.ChoiceField(choices=FORMAT_CHOICES, initial='poules_elimination')
    
    class Meta:
        model = Tournoi
        fields = ['nom', 'type', 'description', 'date_debut', 'date_fin', 'lieu', 'nombre_equipes_max', 'format']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du tournoi'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description détaillée du tournoi...'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lieu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lieu du tournoi'}),
            'nombre_equipes_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '2', 'max': '64'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget.attrs.update({'class': 'form-select'})
        self.fields['format'].widget.attrs.update({'class': 'form-select'})
        
        # Rendre certains champs optionnels
        self.fields['date_fin'].required = False
        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if date_debut and date_fin and date_fin < date_debut:
            raise forms.ValidationError(_("La date de fin doit être postérieure à la date de début."))

        return cleaned_data 