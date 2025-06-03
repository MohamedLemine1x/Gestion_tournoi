# equipes/forms.py
from django import forms
from django.core.validators import FileExtensionValidator
from .models import Equipe, MembreEquipe
from accounts.models import CustomUser

class EquipeForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier une équipe.
    """
    class Meta:
        model = Equipe
        fields = ['nom', 'description', 'logo']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Les Champions, Team Alpha...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez votre équipe : ses objectifs, son histoire, ses valeurs...'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'nom': 'Nom de l\'équipe',
            'description': 'Description',
            'logo': 'Logo de l\'équipe'
        }
        help_texts = {
            'nom': 'Choisissez un nom unique et représentatif pour votre équipe',
            'description': 'Une description détaillée aidera les autres équipes à mieux vous connaître',
            'logo': 'Téléchargez un logo pour votre équipe (format JPG, PNG ou GIF, max 2MB)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Validation du logo
        self.fields['logo'].validators = [
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
                message='Format de fichier non supporté. Utilisez JPG, PNG ou GIF.'
            )
        ]

    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if len(nom) < 3:
            raise forms.ValidationError('Le nom de l\'équipe doit contenir au moins 3 caractères.')
        if Equipe.objects.filter(nom__iexact=nom).exists():
            raise forms.ValidationError('Une équipe avec ce nom existe déjà.')
        return nom

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo:
            if logo.size > 2 * 1024 * 1024:  # 2MB
                raise forms.ValidationError('Le fichier est trop volumineux. Taille maximale : 2MB.')
        return logo

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError('La description doit contenir au moins 10 caractères.')
        return description

class MembreEquipeForm(forms.ModelForm):
    """
    Formulaire pour ajouter un membre à une équipe.
    """
    utilisateur = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(type='invite'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Participant"
    )
    position = forms.ChoiceField(
        choices=[
            ('', 'Sélectionner une position'),
            ('Gardien', 'Gardien'),
            ('Défenseur', 'Défenseur'),
            ('Milieu', 'Milieu de terrain'),
            ('Attaquant', 'Attaquant'),
            ('Entraîneur', 'Entraîneur'),
            ('Remplaçant', 'Remplaçant'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Position dans l'équipe"
    )
    
    class Meta:
        model = MembreEquipe
        fields = ['utilisateur', 'position']
        
    
    def __init__(self, *args, equipe=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si une instance de MembreEquipe est fournie, exclure le champ utilisateur
        if 'instance' in kwargs:
            del self.fields['utilisateur']

        # Si une équipe est spécifiée, excluons les utilisateurs déjà membres
        if equipe:
            membres_existants = equipe.membres.values_list('utilisateur_id', flat=True)
            self.fields['utilisateur'].queryset = CustomUser.objects.filter(
                type='invite'
            ).exclude(
                id__in=membres_existants
            )

    def clean(self):
        cleaned_data = super().clean()
        utilisateur = cleaned_data.get('utilisateur')
        
        # Vérifier si l'utilisateur est déjà dans d'autres équipes
        if utilisateur and MembreEquipe.objects.filter(utilisateur=utilisateur).exists():
            # Nous permettons l'appartenance à plusieurs équipes, mais ajoutons un avertissement
            self.add_warning = f"{utilisateur.username} appartient déjà à une autre équipe"
        
        return cleaned_data

class AjoutMembreEmailForm(forms.Form):
    """
    Formulaire pour ajouter un membre à une équipe par email.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'exemple@email.com'
        }),
        label="Email du participant"
    )
    position = forms.ChoiceField(
        choices=[
            ('Gardien', 'Gardien'),
            ('Défenseur', 'Défenseur'),
            ('Milieu', 'Milieu de terrain'),
            ('Attaquant', 'Attaquant'),
            ('Entraîneur', 'Entraîneur'),
            ('Remplaçant', 'Remplaçant'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'btn-check',
            'style': 'display: none;'
        }),
        label="Position dans l'équipe"
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("L'adresse email est requise.")
            
        # Vérifier si l'email existe déjà dans une équipe
        if MembreEquipe.objects.filter(utilisateur__email=email, is_new=True).exists():
            raise forms.ValidationError(
                "Cet email a déjà reçu une invitation en attente. "
                "Veuillez attendre que l'utilisateur accepte ou refuse l'invitation."
            )
            
        return email