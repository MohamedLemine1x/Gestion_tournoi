from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

class Notification(models.Model):
    """
    Modèle pour stocker les notifications des utilisateurs
    """
    TYPES_NOTIFICATION = (
        ('info', 'Information'),
        ('match_amical', 'Match amical'),
        ('tournoi', 'Tournoi'),
        ('equipe', 'Équipe'),
        ('resultat', 'Résultat'),
    )
    
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    titre = models.CharField(max_length=100)
    message = models.TextField()
    lien = models.CharField(max_length=255, blank=True, null=True)
    date_creation = models.DateTimeField(default=timezone.now)
    lu = models.BooleanField(default=False)
    type_notification = models.CharField(
        max_length=20, 
        choices=TYPES_NOTIFICATION, 
        default='info'
    )
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.titre} - {self.destinataire.username}"
    
    def marquer_comme_lu(self):
        """Marquer la notification comme lue"""
        self.lu = True
        self.save(update_fields=['lu'])
    
    @classmethod
    def creer_notification_globale(cls, titre, message, lien=None, type_notification='info'):
        """
        Crée une notification pour tous les utilisateurs
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        notifications = []
        for user in User.objects.all():
            notifications.append(
                cls(
                    destinataire=user,
                    titre=titre,
                    message=message,
                    lien=lien,
                    type_notification=type_notification
                )
            )
        
        if notifications:
            cls.objects.bulk_create(notifications)
            
    @classmethod
    def creer_notification_match_amical(cls, destinataire, equipe_a, equipe_b, date_match, match_id):
        """
        Crée une notification pour un match amical
        """
        titre = f"Nouveau match amical: {equipe_a.nom} vs {equipe_b.nom}"
        date_formatted = date_match.strftime("%d/%m/%Y à %H:%M")
        message = f"Un match amical a été organisé entre {equipe_a.nom} et {equipe_b.nom} le {date_formatted}."
        lien = reverse('matchs:detail', kwargs={'match_id': match_id})
        
        return cls.objects.create(
            destinataire=destinataire,
            titre=titre,
            message=message,
            lien=lien,
            type_notification='match_amical'
        )
    
    @classmethod
    def creer_notification_equipe(cls, destinataire, equipe, message_perso=None):
        """
        Crée une notification concernant une équipe
        """
        titre = f"Équipe: {equipe.nom}"
        message = message_perso or f"Vous avez été ajouté à l'équipe {equipe.nom}."
        lien = reverse('equipes:detail_equipe', kwargs={'equipe_id': equipe.id})
        
        return cls.objects.create(
            destinataire=destinataire,
            titre=titre,
            message=message,
            lien=lien,
            type_notification='equipe'
        )
    
    @classmethod
    def creer_notification_tournoi(cls, destinataire, tournoi, message_perso=None):
        """
        Crée une notification concernant un tournoi
        """
        titre = f"Tournoi: {tournoi.nom}"
        message = message_perso or f"Votre équipe a été inscrite au tournoi {tournoi.nom}."
        lien = reverse('tournois:detail', kwargs={'tournoi_id': tournoi.id})
        
        return cls.objects.create(
            destinataire=destinataire,
            titre=titre,
            message=message,
            lien=lien,
            type_notification='tournoi'
        )
        
    @classmethod
    def creer_notification_resultat(cls, destinataire, match_id, equipe_a, equipe_b, score_a, score_b, est_tournoi=False):
        """
        Crée une notification de résultat de match
        """
        titre = f"Résultat: {equipe_a.nom} {score_a} - {score_b} {equipe_b.nom}"
        
        if score_a > score_b:
            resultat = f"{equipe_a.nom} a gagné"
        elif score_b > score_a:
            resultat = f"{equipe_b.nom} a gagné"
        else:
            resultat = "Match nul"
            
        message = f"Résultat final: {equipe_a.nom} {score_a} - {score_b} {equipe_b.nom}. {resultat}."
        
        if est_tournoi:
            lien = reverse('tournois:match_detail', kwargs={'match_id': match_id})
            type_notif = 'tournoi'
        else:
            lien = reverse('matchs:detail', kwargs={'match_id': match_id})
            type_notif = 'resultat'
        
        return cls.objects.create(
            destinataire=destinataire,
            titre=titre,
            message=message,
            lien=lien,
            type_notification=type_notif
        )
