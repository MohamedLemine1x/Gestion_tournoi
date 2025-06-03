from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from organisateurs.utils.decorators import organisateur_required
from tournois.models import Tournoi, MatchTournoi, InscriptionTournoi
import logging

logger = logging.getLogger(__name__)

@login_required
@organisateur_required
def dashboard(request):
    """
    Vue du tableau de bord pour les organisateurs.
    Affiche un résumé des tournois, des statistiques et des matchs à venir.
    """
    try:
        today = timezone.now().date()
        organisateur = request.user.organisateur
        logger.info(f"Accès au tableau de bord par l'organisateur {organisateur}")

        # Récupérer les tournois de l'organisateur
        tournois = Tournoi.objects.filter(createur=request.user)
        
        # Statistiques des tournois
        stats_tournois = {
            'total': tournois.count(),
            'en_cours': tournois.filter(
                date_debut__lte=today,
                Q(date_fin__isnull=True) | Q(date_fin__gte=today)
            ).count(),
            'a_venir': tournois.filter(date_debut__gt=today).count(),
            'termines': tournois.filter(date_fin__lt=today).count(),
        }
        
        # Tournois en cours (utilisés dans le tableau principal)
        tournois_en_cours = tournois.filter(
            date_debut__lte=today,
            Q(date_fin__isnull=True) | Q(date_fin__gte=today)
        ).order_by('date_debut')
        
        # Tournois à venir (pour la section des tournois à venir)
        tournois_a_venir = tournois.filter(
            date_debut__gt=today
        ).order_by('date_debut')[:5]
        
        # Matchs à venir pour tous les tournois de l'organisateur
        matchs_a_venir = MatchTournoi.objects.filter(
            tournoi__in=tournois,
            date_match__gt=timezone.now(),
            termine=False
        ).order_by('date_match').select_related('tournoi', 'equipe_domicile', 'equipe_exterieur')[:10]
        
        # Matchs récents
        matchs_recents = MatchTournoi.objects.filter(
            tournoi__in=tournois,
            date_match__lte=timezone.now(),
            termine=True
        ).order_by('-date_match').select_related('tournoi', 'equipe_domicile', 'equipe_exterieur')[:5]
        
        # Récupérer le nombre total de matchs
        total_matchs = MatchTournoi.objects.filter(tournoi__in=tournois).count()

        context = {
            'today': today,
            'stats_tournois': stats_tournois,
            'tournois_en_cours': tournois_en_cours,
            'tournois_a_venir': tournois_a_venir,
            'matchs_a_venir': matchs_a_venir,
            'matchs_recents': matchs_recents,
            'total_matchs': total_matchs,
            'page_title': 'Tableau de bord',
            # Ajouter des liens utiles pour le menu latéral
            'menu_links': [
                {'name': 'Tableau de bord', 'url': 'organisateurs:dashboard', 'icon': 'fa-tachometer-alt'},
                {'name': 'Créer un tournoi', 'url': 'organisateurs:tournoi_create', 'icon': 'fa-plus-circle'},
                {'name': 'Statistiques', 'url': 'organisateurs:statistiques', 'icon': 'fa-chart-bar'},
            ],
        }

        return render(request, 'organisateurs/dashboard.html', context)

    except Exception as e:
        logger.error(f"Erreur dans le tableau de bord: {str(e)}", exc_info=True)
        raise 