from django.urls import path
from . import views

app_name = 'equipes'

urlpatterns = [
    # Gestion de l'équipe
    path('gestion/', views.gestion_equipe, name='gestion_equipe'),
    path('modifier/<int:equipe_id>/', views.modifier_equipe, name='modifier_equipe'),
    path('supprimer/<int:equipe_id>/', views.supprimer_equipe, name='supprimer_equipe'),
    
    # Gestion des membres
    path('membre/<int:id>/modifier/', views.modifier_membre, name='modifier_membre'),
    path('membre/<int:id>/retirer/', views.supprimer_membre, name='retirer_membre'),
    path('api/membre/<int:membre_id>/position/', views.api_modifier_membre_position, name='api_modifier_membre_position'),
    path('<int:equipe_id>/ajout-rapide-membre/', views.ajout_rapide_membre, name='ajout_rapide_membre'),
    path('api/verifier-email/', views.api_verifier_email, name='api_verifier_email'),
    
    # Outils et diagnostics
    path('test-email/', views.test_envoi_email, name='test_email'),
    
    # Autres vues
    path('liste/', views.liste_equipes, name='liste_equipes'),
    path('creer/', views.creer_equipe, name='creer_equipe'),
    path('<int:equipe_id>/', views.detail_equipe, name='detail_equipe'),
]