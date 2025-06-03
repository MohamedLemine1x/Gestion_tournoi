from django.urls import path
from organisateurs.views.match_views import (
    match_create,
    match_edit,
    match_detail,
    match_delete,
    resultat_match
)

urlpatterns = [
    path('nouveau/', match_create, name='match_create'),
    path('<int:pk>/', match_detail, name='match_detail'),
    path('<int:pk>/modifier/', match_edit, name='match_edit'),
    path('<int:pk>/supprimer/', match_delete, name='match_delete'),
    path('<int:pk>/resultat/', resultat_match, name='resultat_match'),
] 