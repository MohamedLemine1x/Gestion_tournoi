from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.liste_notifications, name='liste'),
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    path('<int:notification_id>/marquer-lu/', views.marquer_notification_lue, name='marquer_lue'),
    path('marquer-toutes-lues/', views.marquer_toutes_lues, name='marquer_toutes_lues'),
    path('marquer-groupe-lu/', views.marquer_groupe_lu, name='marquer_groupe_lu'),
    path('<int:notification_id>/supprimer/', views.supprimer_notification, name='supprimer'),
    path('api/get-notifications/', views.get_notifications_ajax, name='get_notifications_ajax'),
] 