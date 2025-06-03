from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
import logging

# Configuration du logger
logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    """
    Page d'accueil personnalisée qui affiche les différents rôles de l'utilisateur
    et permet de choisir comment interagir avec l'application
    """
    user = request.user
    
    # Récupérer le message de redirection s'il existe
    redirect_message = request.session.pop('redirect_message', None)
    
    # Si un message de redirection existe, l'afficher
    if redirect_message:
        messages.warning(request, redirect_message)
    
    # Déterminer les rôles de l'utilisateur
    roles = []
    
    # Vérifier si l'utilisateur est un organisateur
    if user.type == 'organisateur':
        roles.append({
            'name': 'Organisateur de tournoi',
            'icon': 'fas fa-trophy',
            'description': 'Créer et gérer vos tournois, planifier des matchs, suivre les résultats',
            'url': reverse('tournois:liste'),
            'color': 'primary',
            'badge': 'Organisateur',
            'badge_color': 'blue'
        })
    
    # Vérifier si l'utilisateur est un responsable d'équipe
    if user.type == 'responsable':
        # Vérifier si l'utilisateur a déjà une équipe
        has_team = False
        try:
            from equipes.models import Equipe
            from responsables.models import Responsable
            
            # Récupérer d'abord l'objet Responsable
            try:
                responsable = Responsable.objects.get(user=user)
                has_team = Equipe.objects.filter(responsable=responsable).exists()
            except Responsable.DoesNotExist:
                has_team = False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'équipe: {e}")
            pass
        
        roles.append({
            'name': 'Responsable d\'équipe',
            'icon': 'fas fa-users-cog',
            'description': 'Gérer votre équipe, ajouter des joueurs et participer aux tournois',
            'url': reverse('tableau_bord') if 'responsables.urls' in request.path else '/responsables/',
            'color': 'success',
            'badge': 'Équipe existante' if has_team else 'Créer une équipe',
            'badge_color': 'green' if has_team else 'orange'
        })
    
    # Tous les utilisateurs peuvent être participants
    roles.append({
        'name': 'Participant',
        'icon': 'fas fa-user',
        'description': 'Voir les tournois disponibles et les équipes auxquelles vous appartenez',
        'url': reverse('tournois:liste'),
        'color': 'info',
        'badge': 'Participant',
        'badge_color': 'teal'
    })
    
    # Vérifier si l'utilisateur a des préférences enregistrées
    default_role = request.session.get('default_role')
    
    # Si l'utilisateur a un rôle par défaut et qu'il vient d'arriver sur la page (pas via une redirection)
    if default_role and 'no_redirect' not in request.GET and not redirect_message:
        for role in roles:
            if role['name'].lower() == default_role.lower():
                return redirect(role['url'])
    
    # Récupérer les statistiques de l'utilisateur
    user_stats = {
        'tournaments_count': 0,
        'teams_count': 0,
        'matches_count': 0
    }
    
    # Essayer de récupérer des statistiques plus précises
    try:
        # Compteur de tournois
        if user.type == 'organisateur':
            from tournois.models import Tournoi
            user_stats['tournaments_count'] = Tournoi.objects.filter(organisateur=user).count()
        
        # Compteur d'équipes
        if user.type == 'responsable':
            from equipes.models import Equipe
            from responsables.models import Responsable
            
            # Récupérer d'abord l'objet Responsable
            try:
                responsable = Responsable.objects.get(user=user)
                user_stats['teams_count'] = Equipe.objects.filter(responsable=responsable).count()
            except Responsable.DoesNotExist:
                user_stats['teams_count'] = 0
        
        # Compteur de matchs (pour tous les types d'utilisateurs)
        from matchs.models import Match
        from django.db.models import Q
        
        if user.type == 'organisateur':
            # Matchs des tournois organisés
            tournois = Tournoi.objects.filter(organisateur=user)
            user_stats['matches_count'] = Match.objects.filter(tournoi__in=tournois).count()
        elif user.type == 'responsable':
            # Matchs de l'équipe du responsable
            from responsables.models import Responsable
            equipe = None
            
            # Récupérer d'abord l'objet Responsable
            try:
                responsable = Responsable.objects.get(user=user)
                equipe = Equipe.objects.filter(responsable=responsable).first()
            except Responsable.DoesNotExist:
                pass
                
            if equipe:
                user_stats['matches_count'] = Match.objects.filter(
                    Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe)
                ).count()
        else:
            # Matchs des équipes dont l'utilisateur est membre
            from equipes.models import MembreEquipe
            equipes = [membre.equipe for membre in MembreEquipe.objects.filter(utilisateur=user)]
            if equipes:
                user_stats['matches_count'] = Match.objects.filter(
                    Q(equipe_domicile__in=equipes) | Q(equipe_exterieur__in=equipes)
                ).count()
    except Exception as e:
        # En cas d'erreur, continuer avec les statistiques par défaut
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
    
    # Rendu du template avec le contexte
    return render(request, 'dashboard.html', {
        'roles': roles,
        'user': user,
        'user_stats': user_stats,
        'redirect_message': redirect_message
    })

@login_required
def set_default_role(request):
    """
    Définit le rôle par défaut de l'utilisateur
    """
    if request.method == 'POST':
        role = request.POST.get('role')
        if role:
            request.session['default_role'] = role
            messages.success(request, f"Votre rôle par défaut a été défini comme {role}")
    
    return redirect('dashboard')