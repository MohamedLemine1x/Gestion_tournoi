# responsables/urls.py
from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from equipes.models import Equipe

app_name = 'responsables'

urlpatterns = [
    # Tableau de bord principal
    path('', views.tableau_bord_responsable, name='accueil'),
    path('tableau-bord/', views.tableau_bord_responsable, name='tableau_bord'),
   
    # Ajout de membres
    path('ajouter-membre/', views.ajouter_membre, name='ajouter_membre'),
    path('ajouter-membre/<int:equipe_id>/', views.ajouter_membre, name='ajouter_membre_avec_id'),
    path('rechercher-utilisateur/', views.rechercher_utilisateur, name='rechercher_utilisateur'),
    path('selectionner-position/<int:equipe_id>/<int:utilisateur_id>/', views.selectionner_position, name='selectionner_position'),
    path('confirmer-ajout/<int:equipe_id>/<int:utilisateur_id>/', views.confirmer_ajout, name='confirmer_ajout'),
    path('finaliser-ajout/<int:equipe_id>/<int:utilisateur_id>/', views.finaliser_ajout, name='finaliser_ajout'),
    path('equipe/ajouter-membre-email/', views.ajouter_membre_email, name='ajouter_membre_email'),
    
    # Vues des matchs
    path('voir-matches/', views.voir_matches, name='voir_matches'),
    path('voir-resultats/', views.voir_resultats, name='voir_resultats'),
    path('matchs-amicaux/creer/', views.creer_match_amical, name='creer_match_amical'),
    
    # Vues des tournois
    path('voir-tournois/', views.voir_tournois, name='voir_tournois'),
]