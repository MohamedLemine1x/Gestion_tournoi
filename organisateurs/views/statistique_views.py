from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg, Sum, Q, F
from organisateurs.utils.decorators import organisateur_required
from tournois.models import Tournoi
from matchs.models import Match
from equipes.models import Equipe
from joueurs.models import Joueur
import logging

logger = logging.getLogger(__name__)

@login_required
@organisateur_required
def statistiques_tournoi(request, pk):
    """
    Vue pour afficher les statistiques d'un tournoi.
    """
    try:
        tournoi = get_object_or_404(Tournoi, pk=pk, organisateur=request.user.organisateur)
        
        # Statistiques générales
        stats = {
            'nombre_equipes': tournoi.equipes.count(),
            'nombre_matchs': tournoi.matchs.count(),
            'matchs_joues': tournoi.matchs.filter(score_equipe1__isnull=False).count(),
            'matchs_a_venir': tournoi.matchs.filter(score_equipe1__isnull=True).count(),
        }

        # Statistiques des équipes
        equipes_stats = []
        for equipe in tournoi.equipes.all():
            matchs_joues = Match.objects.filter(
                Q(equipe1=equipe) | Q(equipe2=equipe),
                tournoi=tournoi,
                score_equipe1__isnull=False
            )
            
            victoires = matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1__gt=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2__gt=F('score_equipe1'))
            ).count()
            
            defaites = matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1__lt=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2__lt=F('score_equipe1'))
            ).count()
            
            nuls = matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2=F('score_equipe1'))
            ).count()
            
            equipes_stats.append({
                'equipe': equipe,
                'matchs_joues': matchs_joues.count(),
                'victoires': victoires,
                'defaites': defaites,
                'nuls': nuls,
                'points': victoires * 3 + nuls
            })

        # Trier les équipes par points
        equipes_stats.sort(key=lambda x: x['points'], reverse=True)

        context = {
            'tournoi': tournoi,
            'stats': stats,
            'equipes_stats': equipes_stats,
        }
        return render(request, 'organisateurs/statistiques_tournoi.html', context)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des statistiques du tournoi: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de l'affichage des statistiques."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def statistiques_equipe(request, pk):
    """
    Vue pour afficher les statistiques d'une équipe.
    """
    try:
        equipe = get_object_or_404(
            Equipe.objects.filter(tournois__organisateur=request.user.organisateur),
            pk=pk
        )
        
        # Statistiques générales
        matchs_joues = Match.objects.filter(
            Q(equipe1=equipe) | Q(equipe2=equipe),
            score_equipe1__isnull=False
        )
        
        stats = {
            'nombre_matchs': matchs_joues.count(),
            'victoires': matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1__gt=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2__gt=F('score_equipe1'))
            ).count(),
            'defaites': matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1__lt=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2__lt=F('score_equipe1'))
            ).count(),
            'nuls': matchs_joues.filter(
                Q(equipe1=equipe, score_equipe1=F('score_equipe2')) |
                Q(equipe2=equipe, score_equipe2=F('score_equipe1'))
            ).count(),
        }

        # Statistiques des joueurs
        joueurs_stats = []
        for joueur in equipe.joueurs.all():
            matchs_joues = joueur.matchs.filter(
                Q(equipe1=equipe) | Q(equipe2=equipe),
                score_equipe1__isnull=False
            )
            
            joueurs_stats.append({
                'joueur': joueur,
                'matchs_joues': matchs_joues.count(),
                'buts_marques': joueur.buts_marques.count(),
                'passes_decisives': joueur.passes_decisives.count(),
                'cartons_jaunes': joueur.cartons_jaunes.count(),
                'cartons_rouges': joueur.cartons_rouges.count(),
            })

        context = {
            'equipe': equipe,
            'stats': stats,
            'joueurs_stats': joueurs_stats,
        }
        return render(request, 'organisateurs/statistiques_equipe.html', context)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des statistiques de l'équipe: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de l'affichage des statistiques."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def statistiques_joueur(request, pk):
    """
    Vue pour afficher les statistiques d'un joueur.
    """
    try:
        joueur = get_object_or_404(
            Joueur.objects.filter(equipe__tournois__organisateur=request.user.organisateur),
            pk=pk
        )
        
        # Statistiques générales
        matchs_joues = joueur.matchs.filter(score_equipe1__isnull=False)
        
        stats = {
            'nombre_matchs': matchs_joues.count(),
            'buts_marques': joueur.buts_marques.count(),
            'passes_decisives': joueur.passes_decisives.count(),
            'cartons_jaunes': joueur.cartons_jaunes.count(),
            'cartons_rouges': joueur.cartons_rouges.count(),
        }

        # Historique des matchs
        historique_matchs = []
        for match in matchs_joues.order_by('-date_match'):
            historique_matchs.append({
                'match': match,
                'equipe_adverse': match.equipe2 if match.equipe1 == joueur.equipe else match.equipe1,
                'score': f"{match.score_equipe1} - {match.score_equipe2}",
                'buts_marques': joueur.buts_marques.filter(match=match).count(),
                'passes_decisives': joueur.passes_decisives.filter(match=match).count(),
                'cartons': {
                    'jaune': joueur.cartons_jaunes.filter(match=match).exists(),
                    'rouge': joueur.cartons_rouges.filter(match=match).exists(),
                }
            })

        context = {
            'joueur': joueur,
            'stats': stats,
            'historique_matchs': historique_matchs,
        }
        return render(request, 'organisateurs/statistiques_joueur.html', context)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des statistiques du joueur: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de l'affichage des statistiques."))
        return redirect('organisateurs:dashboard') 