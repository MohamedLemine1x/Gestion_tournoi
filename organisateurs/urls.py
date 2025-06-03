from django.urls import path
from . import views

app_name = 'organisateurs'

urlpatterns = [
    # URLs principales
    path('', views.dashboard, name='dashboard'),
    
    # URLs des tournois
    path('tournois/', views.dashboard, name='tournois_liste'),
    path('tournois/nouveau/', views.tournoi_create, name='tournoi_create'),
    path('tournois/<int:pk>/', views.tournoi_edit, name='tournoi_detail'),
    path('tournois/<int:pk>/modifier/', views.tournoi_edit, name='tournoi_edit'),
    
    # URLs des matchs
    path('tournois/<int:tournoi_pk>/matchs/nouveau/', views.match_create, name='match_create'),
    path('matchs/<int:pk>/modifier/', views.match_edit, name='match_edit'),
    path('matchs/<int:pk>/resultat/', views.resultat_match, name='resultat_match'),
    
    # API
    path('api/tournois/<int:tournoi_pk>/equipes/', views.get_equipes_tournoi, name='api_equipes_tournoi'),
] 