# matchs/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Match, Equipe, Tournoi

class MatchForm(forms.ModelForm):
    """Formulaire pour planifier un match dans un tournoi."""
    
    equipe_a = forms.ModelChoiceField(
        queryset=Equipe.objects.none(),  # Sera défini dynamiquement dans __init__
        label="Équipe A",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Sélectionnez l\'équipe A'
        }),
        required=True,
        error_messages={
            'required': "Veuillez sélectionner l'équipe A.",
            'invalid_choice': "Cette équipe n'est pas valide pour ce tournoi."
        }
    )
    
    equipe_b = forms.ModelChoiceField(
        queryset=Equipe.objects.none(),  # Sera défini dynamiquement dans __init__
        label="Équipe B",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Sélectionnez l\'équipe B'
        }),
        required=True,
        error_messages={
            'required': "Veuillez sélectionner l'équipe B.",
            'invalid_choice': "Cette équipe n'est pas valide pour ce tournoi."
        }
    )
    
    date = forms.DateTimeField(
        label="Date et heure du match",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
            'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }),
        initial=timezone.now() + timezone.timedelta(days=1),  # Par défaut, le jour suivant
        required=True,
        error_messages={
            'required': "Veuillez spécifier une date et heure pour le match."
        }
    )
    
    lieu = forms.CharField(
        label="Lieu du match",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Stade municipal, Gymnase central...'
        })
    )
    
    class Meta:
        model = Match
        fields = ['equipe_a', 'equipe_b', 'date', 'lieu']
    
    def __init__(self, *args, **kwargs):
        """Initialise le formulaire avec des équipes spécifiques au tournoi."""
        # Récupérer le tournoi depuis les kwargs
        self.tournoi = kwargs.pop('tournoi', None)
        super().__init__(*args, **kwargs)
        
        if self.tournoi:
            # Définir le queryset pour les équipes
            # Nous assumons une relation ManyToMany entre Equipe et Tournoi
            equipes_queryset = Equipe.objects.filter(tournois=self.tournoi)
            
            # Si aucune équipe n'est associée au tournoi, afficher un message d'avertissement
            if not equipes_queryset.exists():
                equipes_queryset = Equipe.objects.all()
                self.fields['equipe_a'].help_text = "Attention : Aucune équipe n'est associée à ce tournoi. Toutes les équipes sont affichées."
                self.fields['equipe_b'].help_text = "Attention : Aucune équipe n'est associée à ce tournoi. Toutes les équipes sont affichées."
            else:
                self.fields['equipe_a'].help_text = f"Équipes inscrites à ce tournoi ({equipes_queryset.count()})"
                self.fields['equipe_b'].help_text = f"Équipes inscrites à ce tournoi ({equipes_queryset.count()})"
            
            # Définir les querysets
            self.fields['equipe_a'].queryset = equipes_queryset
            self.fields['equipe_b'].queryset = equipes_queryset
            
            # Améliorer les indications du lieu si le tournoi a un lieu
            if self.tournoi.lieu:
                self.fields['lieu'].initial = self.tournoi.lieu
                self.fields['lieu'].help_text = f"Lieu par défaut: {self.tournoi.lieu}"
    
    def clean(self):
        """Valide les données du formulaire."""
        cleaned_data = super().clean()
        equipe_a = cleaned_data.get('equipe_a')
        equipe_b = cleaned_data.get('equipe_b')
        date_match = cleaned_data.get('date')
        
        # Vérifier que les équipes sont différentes
        if equipe_a and equipe_b and equipe_a == equipe_b:
            raise ValidationError("Les deux équipes ne peuvent pas être identiques pour un match.")
        
        # Vérifier que la date est dans le futur
        if date_match and date_match < timezone.now():
            self.add_error('date', "La date du match doit être dans le futur.")
        
        # Vérifier si un match entre ces équipes existe déjà à la même date
        if equipe_a and equipe_b and date_match and self.tournoi:
            # Vérifier le même jour
            date_debut = date_match.replace(hour=0, minute=0, second=0)
            date_fin = date_match.replace(hour=23, minute=59, second=59)
            
            # Exclure le match actuel en cas de modification
            matches_existants = Match.objects.filter(
                tournoi=self.tournoi,
                date__range=(date_debut, date_fin),
                equipe_a__in=[equipe_a, equipe_b],
                equipe_b__in=[equipe_a, equipe_b]
            )
            
            if self.instance.pk:
                matches_existants = matches_existants.exclude(pk=self.instance.pk)
            
            if matches_existants.exists():
                match_existant = matches_existants.first()
                self.add_error('date', 
                    f"Un match impliquant ces équipes est déjà programmé le {match_existant.date.strftime('%d/%m/%Y')} "
                    f"({match_existant.equipe_a.nom} vs {match_existant.equipe_b.nom})."
                )
        
        return cleaned_data