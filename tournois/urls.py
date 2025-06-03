# tournois/urls.py (version simplifiée)
from django.urls import path
from . import views

app_name = 'tournois'

urlpatterns = [
    # URLs publiques des tournois
    path('', views.liste_tournois, name='liste'),
    path('<int:pk>/', views.detail_tournoi, name='detail'),
    path('<int:pk>/resultats/', views.resultats, name='resultats'),
    path('<int:pk>/classement/', views.classement, name='classement'),
    path('<int:pk>/statistiques/', views.statistiques, name='statistiques'),
    
    # URLs pour les inscriptions
    path('<int:pk>/inscrire/', views.inscrire_equipe, name='inscrire'),
    
    # URLs pour les organisateurs (redirigées vers l'app organisateurs)
    path('nouveau/', views.redirect_to_organisateur_create, name='creer'),
    path('<int:pk>/modifier/', views.redirect_to_organisateur_edit, name='modifier'),
    path('<int:pk>/supprimer/', views.supprimer_tournoi, name='supprimer'),
    path('<int:pk>/matchs/nouveau/', views.redirect_to_organisateur_match_create, name='match_create'),
    path('<int:pk>/participants/', views.details_participants, name='details_participants'),
    
    # URL pour planifier les matchs
    path('<int:pk>/planifier-matchs/', views.planifier_matchs, name='planifier_matchs'),
    
    # URLs pour gérer les matchs
    path('match/<int:match_id>/', views.detail_match, name='detail_match'),
    path('match/<int:match_id>/enregistrer-resultat/', views.enregistrer_resultat, name='enregistrer_resultat'),
    path('match/<int:match_id>/supprimer/', views.supprimer_match, name='supprimer_match'),
    
    # Tableau de bord
    path('tableau-bord/', views.tableau_bord, name='tableau_bord'),
]