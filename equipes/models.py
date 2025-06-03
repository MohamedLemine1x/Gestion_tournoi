# equipes/models.py
from django.db import models
from django.conf import settings
from responsables.models import Responsable

class Equipe(models.Model):
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom de l'équipe")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    logo = models.ImageField(upload_to='equipes/logos/', blank=True, null=True, verbose_name="Logo")
    responsable = models.OneToOneField(
        Responsable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipe_geree',
        verbose_name="Responsable"
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    def __str__(self):
        return self.nom
        
    def nombre_membres(self):
        """Retourne le nombre de membres dans l'équipe"""
        return self.membres.count()
        
    def est_complete(self):
        """Vérifie si l'équipe a atteint la limite de 20 membres"""
        return self.nombre_membres() >= 20
        
    def peut_ajouter_membre(self):
        """Vérifie si on peut ajouter un membre à l'équipe"""
        return not self.est_complete()
    
    @property
    def responsable_user(self):
        """Retourne l'utilisateur responsable de l'équipe"""
        return self.responsable.user if self.responsable else None
    
    class Meta:
        verbose_name = "Équipe"
        verbose_name_plural = "Équipes"
        ordering = ['nom']

class MembreEquipe(models.Model):
    POSITIONS_CHOICES = [
        ('', 'Non définie'),
        ('Gardien', 'Gardien'),
        ('Défenseur', 'Défenseur'),
        ('Milieu', 'Milieu de terrain'),
        ('Attaquant', 'Attaquant'),
        ('Entraîneur', 'Entraîneur'),
        ('Remplaçant', 'Remplaçant'),
    ]
    
    equipe = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name='membres')
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='appartenances_equipes'
    )
    position = models.CharField(
        max_length=50, 
        choices=POSITIONS_CHOICES,
        blank=True, 
        null=True,
        verbose_name="Position"
    )
    
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")
    is_new = models.BooleanField(default=True, verbose_name="Nouveau membre")
    
    class Meta:
        unique_together = ('equipe', 'utilisateur')
        verbose_name = "Membre d'équipe"
        verbose_name_plural = "Membres d'équipe"
        ordering = ['position', 'date_ajout']
    
    def __str__(self):
        nom_complet = self.utilisateur.get_full_name()
        nom_affiche = nom_complet if nom_complet else self.utilisateur.username
        return f"{nom_affiche} - {self.equipe.nom}"
        
    def marquer_comme_vu(self):
        """Marque le membre comme ayant été vu (plus nouveau)"""
        if self.is_new:
            self.is_new = False
            self.save()