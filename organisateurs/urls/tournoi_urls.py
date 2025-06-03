from django.urls import path
from organisateurs.views.tournoi_views import (
    tournoi_create,
    tournoi_edit,
    tournoi_detail,
    tournoi_delete
)

urlpatterns = [
    path('nouveau/', tournoi_create, name='tournoi_create'),
    path('<int:pk>/', tournoi_detail, name='tournoi_detail'),
    path('<int:pk>/modifier/', tournoi_edit, name='tournoi_edit'),
    path('<int:pk>/supprimer/', tournoi_delete, name='tournoi_delete'),
] 