from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from functools import wraps
import logging
from organisateurs.models import Organisateur

logger = logging.getLogger(__name__)

def is_organisateur(user):
    """Vérifie si l'utilisateur est un organisateur."""
    logger.debug(f"Vérification du statut organisateur pour l'utilisateur: {user.username} (id: {user.id})")
    try:
        if not user.is_authenticated:
            logger.warning(f"L'utilisateur {user} n'est pas authentifié")
            return False

        exists = hasattr(user, 'organisateur')
        logger.debug(f"Recherche d'une instance Organisateur pour {user.username}: {'Trouvée' if exists else 'Non trouvée'}")
        
        # Si l'utilisateur a le type 'organisateur' mais n'a pas d'instance Organisateur, en créer une
        if not exists and user.type == 'organisateur':
            logger.info(f"Création automatique d'une instance Organisateur pour l'utilisateur {user.username}")
            Organisateur.objects.get_or_create(user=user)
            exists = True
        elif not exists:
            logger.warning(f"Aucune instance Organisateur trouvée pour l'utilisateur {user.username}")
        
        return exists
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut organisateur pour {user.username}: {str(e)}")
        return False

def organisateur_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est un organisateur."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        logger.info("=== Début du décorateur organisateur_required ===")
        logger.info(f"Utilisateur: {request.user}")
        logger.info(f"Est authentifié: {request.user.is_authenticated}")
        logger.info(f"URL demandée: {request.path}")
        logger.info(f"Méthode HTTP: {request.method}")
        
        if not is_organisateur(request.user):
            logger.warning(f"Accès refusé: l'utilisateur {request.user} n'est pas un organisateur")
            messages.error(request, _("Cette section est réservée aux organisateurs de tournois."), extra_tags='login_required access_denied')
            logger.info("=== Fin du décorateur organisateur_required (accès refusé) ===")
            return redirect('home')
            
        logger.info("=== Fin du décorateur organisateur_required (accès autorisé) ===")
        return view_func(request, *args, **kwargs)
    return _wrapped_view 