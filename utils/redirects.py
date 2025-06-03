from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def redirect_by_user_type(request):
    """
    Function to redirect users to their appropriate dashboard based on their user type.
    
    Args:
        request: The HTTP request object containing user information.
        
    Returns:
        HttpResponseRedirect: A redirect to the appropriate dashboard.
    """
    # Get the user and user type
    user = request.user
    
    # Anonymous users should always go to the home page
    if not user.is_authenticated:
        logger.error(f"Anonymous user in redirect_by_user_type, redirecting to home")
        return redirect('home')
        
    user_type = getattr(user, 'type', None)
    
    logger.error(f"==== REDIRECT_BY_USER_TYPE ====")
    logger.error(f"User: {user.username} (ID: {user.id})")
    logger.error(f"User type: {user_type}")
    logger.error(f"Path: {request.path}")
    
    # Détection de boucle de redirection
    if hasattr(request, 'session'):
        redirect_count = request.session.get('redirect_count', 0)
        redirect_path = request.session.get('last_redirect_path', '')
        
        if redirect_path == request.path:
            redirect_count += 1
        else:
            redirect_count = 0
        
        # Si on détecte plus de 3 redirections successives vers le même chemin, 
        # on arrête la boucle et on va à l'accueil
        if redirect_count >= 3:
            logger.error(f"BOUCLE DE REDIRECTION DÉTECTÉE: {request.path}, count={redirect_count}")
            messages.error(request, "Une boucle de redirection a été détectée. Veuillez contacter l'administrateur.")
            request.session['redirect_count'] = 0
            request.session['last_redirect_path'] = ''
            # Rediriger vers une page générique non protégée
            return redirect('tournois:liste')
        
        # Mise à jour des informations de redirection
        request.session['redirect_count'] = redirect_count
        request.session['last_redirect_path'] = request.path
    
    # Check if user type is defined
    if not user_type:
        messages.warning(request, "Votre type d'utilisateur n'est pas défini. Veuillez contacter l'administrateur.")
        return redirect('tournois:liste')
    
    # Redirect based on user type
    if user_type == 'responsable':
        return redirect('responsables:tableau_bord')
    elif user_type == 'organisateur':
        # Vérifier si l'utilisateur a un profil d'organisateur valide
        if not hasattr(user, 'organisateur'):
            logger.error(f"L'utilisateur {user.username} est de type organisateur mais n'a pas de profil organisateur")
            messages.warning(request, "Votre profil d'organisateur est incomplet. Veuillez contacter l'administrateur.")
            return redirect('tournois:liste')
        return redirect('organisateurs:dashboard')
    elif user_type == 'participant':
        # Vérifier si l'utilisateur a des équipes avant de le rediriger vers le tableau de bord
        try:
            from equipes.models import MembreEquipe
            has_teams = MembreEquipe.objects.filter(utilisateur=user).exists()
            
            if not has_teams:
                # Si l'utilisateur n'a pas d'équipes, le rediriger vers la liste des tournois
                messages.info(request, "Vous n'avez pas encore d'équipe. Consultez les tournois disponibles pour trouver une équipe.")
                return redirect('tournois:liste')
            return redirect('participants:tableau_bord')
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des équipes pour {user.username}: {str(e)}")
            return redirect('tournois:liste')
    else:
        # Default redirection if user type is not recognized
        messages.warning(request, f"Type d'utilisateur '{user_type}' non reconnu. Veuillez contacter l'administrateur.")
        return redirect('tournois:liste') 