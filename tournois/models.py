# tournois/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from equipes.models import Equipe as EquipePrincipale  # Importation claire

def tournament_logo_path(instance, filename):
    # Les logos seront stockés dans MEDIA_ROOT/tournament_logos/tournament_<id>/<filename>
    return f'tournament_logos/tournament_{instance.id}/{filename}'

class Tournoi(models.Model):
    """Modèle pour représenter un tournoi de football"""
    nom = models.CharField(max_length=100, verbose_name="Nom du tournoi")
    description = models.TextField(blank=True, verbose_name="Description")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(blank=True, null=True, verbose_name="Date de fin")
    lieu = models.CharField(max_length=100, blank=True, verbose_name="Lieu")
    nombre_equipes_max = models.PositiveIntegerField(default=16, verbose_name="Nombre maximum d'équipes")
    createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tournois_crees")
    date_creation = models.DateTimeField(default=timezone.now)
    logo = models.ImageField(upload_to=tournament_logo_path, blank=True, null=True, verbose_name="Logo du tournoi")
    
    class Meta:
        verbose_name = "Tournoi"
        verbose_name_plural = "Tournois"
        ordering = ['-date_creation']
    
    def __str__(self):
        return self.nom
    
    def est_termine(self):
        """Vérifie si le tournoi est terminé"""
        if self.date_fin:
            return timezone.now().date() > self.date_fin
        return timezone.now().date() > self.date_debut
        
    @property
    def organisateur(self):
        """Renvoie le créateur du tournoi (alias pour compatibilité)"""
        return self.createur

class InscriptionTournoi(models.Model):
    """Modèle pour lier une équipe principale à un tournoi"""
    equipe = models.ForeignKey(EquipePrincipale, on_delete=models.CASCADE, related_name="inscriptions_tournois")
    tournoi = models.ForeignKey(Tournoi, on_delete=models.CASCADE, related_name="inscriptions")
    date_inscription = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Inscription à un tournoi"
        verbose_name_plural = "Inscriptions aux tournois"
        unique_together = ['equipe', 'tournoi']
    
    def __str__(self):
        return f"{self.equipe.nom} - {self.tournoi.nom}"

class MatchTournoi(models.Model):
    """Modèle pour représenter un match entre deux équipes dans un tournoi"""
    tournoi = models.ForeignKey(Tournoi, on_delete=models.CASCADE,  related_name='matchs_tournoi')
    equipe_domicile = models.ForeignKey(EquipePrincipale, on_delete=models.CASCADE, related_name="matchs_domicile")
    equipe_exterieur = models.ForeignKey(EquipePrincipale, on_delete=models.CASCADE, related_name="matchs_exterieur")
    date_match = models.DateTimeField(verbose_name="Date et heure du match")
    lieu_match = models.CharField(max_length=100, blank=True, verbose_name="Lieu du match")
    arbitre = models.CharField(max_length=100, blank=True, verbose_name="Arbitre")
    remarques = models.TextField(blank=True, verbose_name="Remarques")
    score_domicile = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Score équipe domicile")
    score_exterieur = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Score équipe extérieure")
    termine = models.BooleanField(default=False, verbose_name="Match terminé")
    
    class Meta:
        verbose_name = "Match de tournoi"
        verbose_name_plural = "Matchs de tournoi"
        ordering = ['date_match']
    
    def __str__(self):
        return f"{self.equipe_domicile.nom} vs {self.equipe_exterieur.nom}"
    
    def vainqueur(self):
        """Retourne l'équipe vainqueur ou None en cas de match nul"""
        if not self.termine or self.score_domicile is None or self.score_exterieur is None:
            return None
        
        if self.score_domicile > self.score_exterieur:
            return self.equipe_domicile
        elif self.score_exterieur > self.score_domicile:
            return self.equipe_exterieur
        else:
            return None  # Match nul