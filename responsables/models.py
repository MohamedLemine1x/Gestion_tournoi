# responsables/models.py
from django.db import models
from django.conf import settings

class Responsable(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # Au lieu de User
        on_delete=models.CASCADE, 
        related_name='responsable_profile'
    )
    telephone = models.CharField(max_length=20, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    class Meta:
        verbose_name = "Responsable d'équipe"
        verbose_name_plural = "Responsables d'équipe"