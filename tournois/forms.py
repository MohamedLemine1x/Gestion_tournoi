# tournois/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Tournoi, Equipe, Match, Resultat

class TournoiForm(forms.ModelForm):
    """Formulaire pour créer ou modifier un tournoi"""
    class Meta:
        model = Tournoi
        fields = ['nom', 'description', 'date_debut', 'date_fin', 'lieu']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_fin and date_debut and date_fin < date_debut:
            raise ValidationError("La date de fin ne peut pas être antérieure à la date de début.")
        
        return cleaned_data

class EquipeForm(forms.ModelForm):
    """Formulaire pour inscrire une équipe"""
    class Meta:
        model = Equipe
        fields = ['nom', 'responsable', 'email', 'telephone']
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        tournoi = self.instance.tournoi if hasattr(self.instance, 'tournoi') and self.instance.tournoi else None
        
        # Vérifier l'unicité du nom d'équipe dans le tournoi
        if tournoi and Equipe.objects.filter(nom=nom, tournoi=tournoi).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
            raise ValidationError("Une équipe avec ce nom existe déjà dans ce tournoi.")
        
        return nom

class MatchForm(forms.ModelForm):
    """Formulaire pour créer ou modifier un match"""
    class Meta:
        model = Match
        fields = ['equipe_domicile', 'equipe_exterieur', 'date_match', 'lieu_match', 'arbitre', 'remarques']
        widgets = {
            'date_match': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'remarques': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        tournoi = kwargs.pop('tournoi', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les équipes par tournoi
        if tournoi:
            self.fields['equipe_domicile'].queryset = Equipe.objects.filter(tournoi=tournoi)
            self.fields['equipe_exterieur'].queryset = Equipe.objects.filter(tournoi=tournoi)
    
    def clean(self):
        cleaned_data = super().clean()
        equipe_domicile = cleaned_data.get('equipe_domicile')
        equipe_exterieur = cleaned_data.get('equipe_exterieur')
        
        if equipe_domicile and equipe_exterieur and equipe_domicile == equipe_exterieur:
            raise ValidationError("Une équipe ne peut pas jouer contre elle-même.")
        
        return cleaned_data

class ResultatForm(forms.ModelForm):
    """Formulaire pour enregistrer le résultat d'un match"""
    class Meta:
        model = Resultat
        fields = ['score_domicile', 'score_exterieur', 'commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }

# Formulaire personnalisé pour l'inscription rapide de plusieurs équipes
class EquipesRapidesForm(forms.Form):
    """Formulaire pour inscrire plusieurs équipes rapidement"""
    equipes = forms.CharField(
        label="Noms des équipes (une par ligne)",
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Entrez un nom d\'équipe par ligne'})
    )
    
    def clean_equipes(self):
        equipes_text = self.cleaned_data.get('equipes')
        equipes_list = [equipe.strip() for equipe in equipes_text.split('\n') if equipe.strip()]
        
        if len(equipes_list) < 2:
            raise ValidationError("Veuillez entrer au moins deux équipes.")
        
        # Vérifier les doublons
        if len(equipes_list) != len(set(equipes_list)):
            raise ValidationError("Les noms d'équipes doivent être uniques.")
        
        return equipes_list

# Formulaire de recherche pour les tournois
class TournoiSearchForm(forms.Form):
    """Formulaire pour rechercher des tournois"""
    recherche = forms.CharField(
        required=False, 
        label="Rechercher",
        widget=forms.TextInput(attrs={'placeholder': 'Nom du tournoi'})
    )
    date_debut = forms.DateField(
        required=False,
        label="À partir de",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_fin = forms.DateField(
        required=False,
        label="Jusqu'à",
        widget=forms.DateInput(attrs={'type': 'date'})
    )