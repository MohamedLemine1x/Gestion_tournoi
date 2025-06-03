# tournoi_foot/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from accounts import views as accounts_views  # Réimportez les vues des comptes

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Include app URLs with namespaces
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('tournois/', include('tournois.urls', namespace='tournois')),
    path('equipes/', include('equipes.urls', namespace='equipes')),
    path('matchs/', include('matchs.urls', namespace='matchs')),
    path('statistiques/', include('statistiques.urls', namespace='statistiques')),
    path('responsables/', include('responsables.urls', namespace='responsables')),
    path('participants/', include('participants.urls', namespace='participants')),
    path('organisateurs/', include('organisateurs.urls', namespace='organisateurs')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    
    # Add back direct shortcuts to common auth URLs for convenience
    path('profile/', accounts_views.profile_view, name='profile'),
    path('logout/', accounts_views.logout_view, name='logout'),
    
    # Ajoutez la vue de tableau de bord
    path('dashboard/', accounts_views.dashboard_view, name='dashboard'),
    
    # Redirect to the home page
    path('', accounts_views.home, name='home'),
    
    # Correct the redirect (change source path to avoid loop)
    path('mes-tournois/', RedirectView.as_view(url='/tournois/', permanent=True)),
    
    # Redirect old login URL to the namespaced version
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=True)),
    
    # Exemples d'icônes de football
    path('football-icon-example/', TemplateView.as_view(template_name='football_icon_example.html'), name='football_icon_example'),
    path('match-example/', TemplateView.as_view(template_name='matchs/match_detail_example.html'), name='match_example'),
    
    # Homepage and common URLs
    path('search/', TemplateView.as_view(template_name='search.html'), name='search'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('faq/', TemplateView.as_view(template_name='faq.html'), name='faq'),
    
    # Favicon route
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('img/favicon.png')), name='favicon'),
]

# Handle media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)