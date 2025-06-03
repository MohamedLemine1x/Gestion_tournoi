# backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import logging

# Configurer le logger
logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    """
    Backend d'authentification qui permet l'authentification par email en plus du nom d'utilisateur.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authentifie un utilisateur en utilisant l'email ou le nom d'utilisateur.
        
        Args:
            request: La requête HTTP
            username: Email ou nom d'utilisateur de l'utilisateur
            password: Mot de passe de l'utilisateur
            
        Returns:
            L'utilisateur authentifié si les identifiants sont valides, None sinon.
        """
        logger.info(f"EmailBackend: Tentative d'authentification pour {username}")
        
        UserModel = get_user_model()
        
        try:
            # Chercher l'utilisateur par email ou username
            user = UserModel.objects.filter(
                Q(email__iexact=username) | Q(username__iexact=username)
            ).first()
            
            if user:
                logger.info(f"EmailBackend: Utilisateur trouvé: {user.email}")
                
                # Vérifier si l'utilisateur est actif
                if not user.is_active:
                    logger.info(f"EmailBackend: Utilisateur inactif: {user.email}")
                    return None
                
                # Vérifier le mot de passe
                if user.check_password(password):
                    logger.info(f"EmailBackend: Authentification réussie pour {user.email}")
                    return user
                else:
                    logger.info(f"EmailBackend: Échec d'authentification - mot de passe incorrect pour {user.email}")
                    return None
            else:
                logger.info(f"EmailBackend: Aucun utilisateur trouvé pour {username}")
                return None
                
        except Exception as e:
            logger.error(f"EmailBackend: Erreur d'authentification: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Récupère un utilisateur par son ID.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            L'utilisateur correspondant à l'ID, None si non trouvé
        """
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None