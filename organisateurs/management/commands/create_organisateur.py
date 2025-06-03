from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from organisateurs.models import Organisateur
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = "Crée une instance Organisateur pour un utilisateur existant"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nom d\'utilisateur ou email de l\'utilisateur')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        
        # Chercher l'utilisateur par nom d'utilisateur ou email
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Utilisateur "{username}" introuvable'))
                return
        
        # Vérifier si l'utilisateur a déjà une instance Organisateur
        if hasattr(user, 'organisateur'):
            self.stdout.write(self.style.WARNING(f'L\'utilisateur "{user.username}" a déjà une instance Organisateur'))
            return
        
        # Mettre à jour le type d'utilisateur et créer l'instance Organisateur
        with transaction.atomic():
            user.type = 'organisateur'
            user.save()
            
            organisateur = Organisateur.objects.create(user=user)
            
            self.stdout.write(self.style.SUCCESS(f'Instance Organisateur créée avec succès pour "{user.username}"')) 