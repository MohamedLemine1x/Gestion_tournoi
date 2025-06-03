# matchs/urls.py
from django.urls import path
from . import views

app_name = 'matchs'

urlpatterns = [
    # URLs publiques des matchs
    path('', views.liste_matchs, name='liste'),
    path('<int:pk>/', views.detail_match, name='detail'),
    
    # URLs pour les responsables d'équipes
    path('nouveau/', views.creer_match, name='creer_match'),
    path('<int:pk>/modifier/', views.modifier_match, name='modifier'),
    path('<int:pk>/supprimer/', views.supprimer_match, name='supprimer'),
    path('<int:pk>/enregistrer-resultat/', views.enregistrer_resultat, name='enregistrer_resultat'),
    
    # Redirection vers les tournois
    path('tournois/', views.liste_tournois, name='tournois_liste'),
]