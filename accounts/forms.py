from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile
import logging
from django.contrib.auth import get_user_model


class CustomUserCreationForm(UserCreationForm):
    """
    Formulaire d'inscription pour les utilisateurs personnalisés.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password1', 'password2', 'type')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur"}),
            'type': forms.Select(attrs={'class': 'form-select'})
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return email


class LoginForm(AuthenticationForm):
    """
    Formulaire de connexion personnalisé avec email au lieu de nom d'utilisateur.
    """
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )
    remember = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class RegisterForm(UserCreationForm):
    """
    Formulaire d'inscription avec champs additionnels pour le profil.
    """
    # Champs utilisateur
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur"})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmez le mot de passe'})
    )
    type = forms.ChoiceField(
        choices=CustomUser.TYPE_CHOICES,
        required=True,
        label="Type de compte",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    agreeTerms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions d'utilisation",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'type')
    
    def clean_email(self):
        """Validation personnalisée pour l'email."""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return email
    
    def save(self, commit=True):
        """Sauvegarde l'utilisateur et son profil."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.type = self.cleaned_data['type']
        
        if commit:
            user.save()
            # Le signal post_save s'occupera de créer le profil
        
        return user


class ProfileForm(forms.ModelForm):
    """
    Formulaire simplifié pour modifier le profil utilisateur.
    Ne contient que les champs username et email.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    
    class Meta:
        model = Profile
        fields = []  # Aucun champ du modèle Profile n'est modifiable
    
    def __init__(self, *args, **kwargs):
        """Initialise les champs avec les valeurs de l'utilisateur."""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        """Ne fait rien car les champs sont en lecture seule."""
        return self.instance


class AvatarForm(forms.ModelForm):
    """
    Formulaire pour modifier uniquement l'avatar du profil.
    """
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Profile
        fields = ('avatar',)
    
    def clean_avatar(self):
        """Validation personnalisée pour l'avatar."""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Vérifier la taille et le type de fichier
            if avatar.size > 5 * 1024 * 1024:  # 5 MB
                raise ValidationError("La taille de l'image ne doit pas dépasser 5 Mo.")
                
            # Vérifier l'extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
            import os
            ext = os.path.splitext(avatar.name)[1][1:].lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"Seuls les formats suivants sont autorisés: {', '.join(allowed_extensions)}")
                
            return avatar
        return None


class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulaire personnalisé pour la réinitialisation de mot de passe.
    Utilisé par CustomPasswordResetView.
    Hérite de PasswordResetForm.
    """
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )


class DeleteAccountForm(forms.Form):
    """
    Formulaire pour confirmer la suppression de compte.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Votre mot de passe'}),
        required=True,
        label="Mot de passe actuel"
    )
    confirm_delete = forms.BooleanField(
        required=True,
        label="Je confirme vouloir supprimer définitivement mon compte",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )