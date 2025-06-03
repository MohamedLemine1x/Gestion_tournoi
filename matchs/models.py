# matchs/models.py
from django.db import models
from tournois.models import Tournoi  # Importez Tournoi depuis l'app appropriée
from equipes.models import Equipe

class Match(models.Model):
    TYPES_MATCH = (
        ('tournoi', 'Match de tournoi'),
        ('amical', 'Match amical'),
    )
    
    tournoi = models.ForeignKey(Tournoi, on_delete=models.SET_NULL, null=True, related_name='matchs_amicaux')
    equipe_a = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name='matchs_equipe_a')
    equipe_b = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name='matchs_equipe_b')
    date = models.DateTimeField()
    lieu = models.CharField(max_length=100, blank=True, null=True)
    score_equipe_a = models.PositiveIntegerField(blank=True, null=True)
    score_equipe_b = models.PositiveIntegerField(blank=True, null=True)
    termine = models.BooleanField(default=False)
    type_match = models.CharField(max_length=10, choices=TYPES_MATCH, default='tournoi')
    notes = models.TextField(blank=True, null=True, verbose_name="Notes supplémentaires")
    
    def __str__(self):
        score = ""
        if self.score_equipe_a is not None and self.score_equipe_b is not None:
            score = f" ({self.score_equipe_a} - {self.score_equipe_b})"
        return f"{self.equipe_a.nom} vs {self.equipe_b.nom}{score}"
    
    def vainqueur(self):
        """Retourne l'équipe gagnante ou None en cas de match nul."""
        if not self.termine or self.score_equipe_a is None or self.score_equipe_b is None:
            return None
        
        if self.score_equipe_a > self.score_equipe_b:
            return self.equipe_a
        elif self.score_equipe_b > self.score_equipe_a:
            return self.equipe_b
        else:
            return None  # Match nul
            
    def est_amical(self):
        """Indique si le match est amical (sans tournoi associé)"""
        return self.type_match == 'amical'