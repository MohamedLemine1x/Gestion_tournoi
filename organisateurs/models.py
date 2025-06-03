from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from tournois.models import Tournoi
from matchs.models import Match

class Organisateur(models.Model):
    """
    Modèle pour les organisateurs de tournois.
    Chaque organisateur est lié à un utilisateur CustomUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organisateur',
        verbose_name=_("Utilisateur")
    )
    
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création")
    )
    
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière modification")
    )
    
    def __str__(self):
        return f"Organisateur: {self.user.get_full_name() or self.user.username}"
    
    def get_tournois_organises(self):
        """Retourne tous les tournois organisés par cet organisateur."""
        return Tournoi.objects.filter(createur=self.user)
    
    def get_matchs_a_planifier(self):
        """Retourne tous les matchs à planifier pour les tournois de l'organisateur."""
        tournois_ids = self.get_tournois_organises().values_list('id', flat=True)
        return Match.objects.filter(tournoi_id__in=tournois_ids, date_match__isnull=True)
    
    def get_matchs_a_arbitrer(self):
        """Retourne tous les matchs à arbitrer pour les tournois de l'organisateur."""
        tournois_ids = self.get_tournois_organises().values_list('id', flat=True)
        return Match.objects.filter(
            tournoi_id__in=tournois_ids,
            date_match__isnull=False,
            score_equipe_a__isnull=True,
            score_equipe_b__isnull=True
        )
    
    class Meta:
        verbose_name = _("Organisateur")
        verbose_name_plural = _("Organisateurs")
        ordering = ['-date_creation']

# Signal pour créer automatiquement une instance Organisateur quand un utilisateur est créé ou modifié avec type='organisateur'
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_organisateur(sender, instance, created, **kwargs):
    """
    Crée ou met à jour automatiquement une instance Organisateur lorsqu'un utilisateur
    est créé ou modifié avec le type 'organisateur'.
    """
    # Vérifier si l'utilisateur est de type 'organisateur'
    if instance.type == 'organisateur':
        # Vérifier si une instance Organisateur existe déjà
        if not hasattr(instance, 'organisateur'):
            # Créer une nouvelle instance Organisateur
            Organisateur.objects.create(user=instance)
            print(f"Instance Organisateur créée automatiquement pour {instance.username}")
