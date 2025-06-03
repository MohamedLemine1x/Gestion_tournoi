from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import re

class UserAccessMiddleware:
    """
    Middleware pour gérer les restrictions d'accès basées sur le type d'utilisateur.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Définir les URLs autorisées pour chaque type d'utilisateur
        self.allowed_urls = {
            'participant': [
                r'^/accounts/profile/$',  # Page de profil
                r'^/accounts/profile/update/$',  # Mise à jour du profil
                r'^/accounts/logout/$',  # Déconnexion
                r'^/tournois/liste/$',  # Liste des tournois
                r'^/equipes/mon-equipe/$',  # Vue de l'équipe
                r'^/matchs/resultats/$',  # Résultats des matchs
                r'^/static/',  # Fichiers statiques
                r'^/media/',  # Fichiers média
            ],
            'responsable': [
                r'^/accounts/profile/.*$',  # Toutes les pages de profil
                r'^/accounts/logout/$',
                r'^/responsables/.*$',  # Toutes les pages responsables
                r'^/equipes/.*$',  # Toutes les pages équipes
                r'^/matchs/.*$',  # Toutes les pages matchs
                r'^/static/',
                r'^/media/',
            ],
            'organisateur': [
                r'^/.*$',  # Accès à tout pour les organisateurs
            ]
        }

    def __call__(self, request):
        # Si l'utilisateur n'est pas authentifié, laisser passer
        if not request.user.is_authenticated:
            return self.get_response(request)

        user_type = getattr(request.user, 'type', None)
        if not user_type:
            return self.get_response(request)

        # Obtenir le chemin de l'URL actuelle
        path = request.path_info

        # Vérifier si l'URL est autorisée pour ce type d'utilisateur
        allowed_patterns = self.allowed_urls.get(user_type, [])
        is_allowed = any(re.match(pattern, path) for pattern in allowed_patterns)

        if not is_allowed:
            messages.error(
                request,
                "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
            )
            # Rediriger vers la page appropriée selon le type d'utilisateur
            if user_type == 'participant':
                return redirect('accounts:profile')
            elif user_type == 'responsable':
                return redirect('responsables:tableau_bord')
            elif user_type == 'organisateur':
                return redirect('organisateurs:dashboard')
            else:
                return redirect('home')

        return self.get_response(request) 