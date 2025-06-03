from django.urls import path
from organisateurs.views.dashboard_views import dashboard

urlpatterns = [
    path('', dashboard, name='dashboard'),
] 