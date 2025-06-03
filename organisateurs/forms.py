from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Organisateur
from tournois.models import Tournoi
from matchs.models import Match

class OrganisateurForm(forms.ModelForm):
    """Formulaire pour la création et la modification d'un organisateur."""
    class Meta:
        model = Organisateur
        fields = ['user']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'})
        }

class TournoiForm(forms.ModelForm):
    """Formulaire pour la création et la modification d'un tournoi."""
    class Meta:
        model = Tournoi
        fields = ['nom', 'description', 'date_debut', 'date_fin', 'lieu', 'nombre_equipes_max']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_debut': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'date_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'lieu': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_equipes_max': forms.NumberInput(attrs={'class': 'form-control'})
        }

class MatchForm(forms.ModelForm):
    """Formulaire pour la planification et la gestion des matchs."""
    class Meta:
        model = Match
        fields = ['equipe_a', 'equipe_b', 'date', 'lieu']
        widgets = {
            'equipe_a': forms.Select(attrs={'class': 'form-control'}),
            'equipe_b': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'lieu': forms.TextInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        self.tournoi = kwargs.pop('tournoi', None)
        super().__init__(*args, **kwargs)
        
        if self.tournoi:
            # Filtrer les équipes pour n'afficher que celles du tournoi
            self.fields['equipe_a'].queryset = self.tournoi.equipes.all()
            self.fields['equipe_b'].queryset = self.tournoi.equipes.all()
            
            # Définir le lieu par défaut si le tournoi en a un
            if self.tournoi.lieu:
                self.fields['lieu'].initial = self.tournoi.lieu

    def clean(self):
        cleaned_data = super().clean()
        equipe_a = cleaned_data.get('equipe_a')
        equipe_b = cleaned_data.get('equipe_b')
        date = cleaned_data.get('date')

        if equipe_a and equipe_b and equipe_a == equipe_b:
            raise forms.ValidationError(_("Les deux équipes ne peuvent pas être identiques."))

        if date and date < timezone.now():
            raise forms.ValidationError(_("La date du match doit être dans le futur."))

        return cleaned_data

class ResultatMatchForm(forms.ModelForm):
    """Formulaire pour la saisie des résultats des matchs."""
    class Meta:
        model = Match
        fields = ['score_equipe_a', 'score_equipe_b']
        widgets = {
            'score_equipe_a': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'score_equipe_b': forms.NumberInput(attrs={'class': 'form-control', 'min': 0})
        }

    def clean(self):
        cleaned_data = super().clean()
        score_a = cleaned_data.get('score_equipe_a')
        score_b = cleaned_data.get('score_equipe_b')

        if score_a is not None and score_a < 0:
            raise forms.ValidationError(_("Le score de l'équipe A ne peut pas être négatif."))

        if score_b is not None and score_b < 0:
            raise forms.ValidationError(_("Le score de l'équipe B ne peut pas être négatif."))

        return cleaned_data 