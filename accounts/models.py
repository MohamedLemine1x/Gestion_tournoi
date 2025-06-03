from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
import os

def validate_file_size(value):
    """Valide la taille du fichier (max 5MB)."""
    filesize = value.size
    
    if filesize > 5 * 1024 * 1024:  # 5MB
        raise ValidationError("La taille maximale de l'image est de 5 Mo.")
    return value

def avatar_upload_path(instance, filename):
    """Définit le chemin d'upload pour les avatars."""
    # Obtenir l'extension du fichier
    ext = filename.split('.')[-1]
    # Renommer le fichier avec l'ID de l'utilisateur
    filename = f"{instance.user.id}-avatar.{ext}"
    return os.path.join('avatars', filename)


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec email comme identifiant
    et champ type pour distinguer les différents rôles
    """
    
    # Choix des types d'utilisateurs
    PARTICIPANT = 'participant'
    RESPONSABLE = 'responsable'
    ORGANISATEUR = 'organisateur'
    ADMIN = 'admin'
    
    TYPE_CHOICES = [
        (PARTICIPANT, 'Participant'),
        (RESPONSABLE, 'Responsable'),
        (ORGANISATEUR, 'Organisateur'),
        (ADMIN, 'Administrateur'),
    ]
    
    email = models.EmailField(_('email address'), unique=True)
    type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default=PARTICIPANT,
        verbose_name="Type d'utilisateur"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_derniere_connexion = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Liste des champs requis à la création d'un superuser
    
    objects = UserManager()
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Si c'est un nouveau compte organisateur, créer un profil organisateur
        if is_new and self.type == self.ORGANISATEUR:
            from organisateurs.models import Organisateur
            Organisateur.objects.get_or_create(user=self)
        
    @property
    def display_name(self):
        """
        Retourne un nom d'affichage pour l'utilisateur (prénom + nom ou username)
        """
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username or self.email
    
    @property
    def is_participant(self):
        """Vérifie si l'utilisateur est un participant."""
        return self.type == self.PARTICIPANT
    
    @property
    def is_responsable(self):
        """Vérifie si l'utilisateur est un responsable d'équipe."""
        return self.type == self.RESPONSABLE
    
    @property
    def is_organisateur(self):
        """Vérifie si l'utilisateur est un organisateur de tournoi."""
        return self.type == self.ORGANISATEUR


class NotificationPreference(models.Model):
    """
    Modèle pour stocker les préférences de notification des utilisateurs
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="notification_preferences")
    
    # Préférences générales
    enable_all = models.BooleanField(default=True, verbose_name="Activer toutes les notifications")
    sound_enabled = models.BooleanField(default=True, verbose_name="Activer les sons de notification")
    
    # Préférences par type de notification
    match_notifications = models.BooleanField(default=True, verbose_name="Notifications de matchs")
    tournament_notifications = models.BooleanField(default=True, verbose_name="Notifications de tournois")
    team_notifications = models.BooleanField(default=True, verbose_name="Notifications d'équipe")
    result_notifications = models.BooleanField(default=True, verbose_name="Notifications de résultats")
    
    # Préférences de livraison
    email_delivery = models.BooleanField(default=True, verbose_name="Recevoir par email")
    push_delivery = models.BooleanField(default=False, verbose_name="Notifications push")
    
    # Configuration du digest (résumé quotidien/hebdomadaire)
    digest_enabled = models.BooleanField(default=False, verbose_name="Activer le résumé des notifications")
    DIGEST_CHOICES = [
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
    ]
    digest_frequency = models.CharField(max_length=10, choices=DIGEST_CHOICES, default='daily', verbose_name="Fréquence du résumé")
    
    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"
    
    def __str__(self):
        return f"Préférences de notification pour {self.user}"


class Profile(models.Model):
    """Modèle de profil utilisateur étendu"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    date_naissance = models.DateField(null=True, blank=True)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    code_postal = models.CharField(max_length=10, blank=True, null=True)
    pays = models.CharField(max_length=50, blank=True, null=True)
    preference_langue = models.CharField(max_length=10, default='fr')
    preferences = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Profil de {self.user.username}"
    
    @property
    def nom_complet(self):
        """Retourne le nom complet de l'utilisateur."""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal pour créer automatiquement un profil lorsqu'un utilisateur est créé
    """
    if created:
        Profile.objects.create(user=instance)
        # Créer également les préférences de notification par défaut
        NotificationPreference.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal pour sauvegarder automatiquement un profil lorsqu'un utilisateur est sauvegardé
    """
    instance.profile.save()