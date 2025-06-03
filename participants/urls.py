from django.urls import path
from . import views

app_name = 'participants'

urlpatterns = [
    # Tableau de bord participant (liste des équipes)
    path('', views.tableau_bord_participant, name='tableau_bord'),
    
    # Calendrier et résultats pour une équipe spécifique du participant
    path('equipe/<int:equipe_id>/calendrier-resultats/', views.voir_calendrier_resultats_participant, name='voir_calendrier_resultats_participant'),
    
    # Matchs amicaux pour une équipe spécifique du participant
    path('equipe/<int:equipe_id>/matchs-amicaux/', views.voir_matchs_amicaux, name='voir_matchs_amicaux'),
    
    # Vue des tournois disponibles
    path('tournois-disponibles/', views.voir_tournois_disponibles, name='voir_tournois_disponibles'),
    
    # Nouvelles vues pour les équipes et matchs de l'utilisateur
    path('mes-equipes/', views.mes_equipes_view, name='mes_equipes'),
    path('mes-matchs/', views.mes_matchs_view, name='mes_matchs'),
] 