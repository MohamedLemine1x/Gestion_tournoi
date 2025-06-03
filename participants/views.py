from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from equipes.models import MembreEquipe, Equipe # Importer les modèles nécessaires
from tournois.models import MatchTournoi, Tournoi, InscriptionTournoi # Ajout de Tournoi et InscriptionTournoi
from matchs.models import Match # Importer le modèle de match amical
from django.db.models import Q
from django.utils import timezone
from equipes.views import participant_required
import logging

# Create your views here.

logger = logging.getLogger(__name__)

@login_required
def tableau_bord_participant(request):
    """
    Vue du tableau de bord pour les participants.
    Affiche les équipes dont l'utilisateur est membre et les prochains matchs.
    """
    try:
        # Récupérer les équipes du participant avec prefetch_related pour optimiser les requêtes
        membre_equipes = MembreEquipe.objects.filter(
            utilisateur=request.user
        ).select_related(
            'equipe',
            'equipe__responsable',
            'equipe__responsable__user'
        ).prefetch_related(
            'equipe__inscriptions_tournois',
            'equipe__membres',
            'equipe__membres__utilisateur'
        )
        
        # Préparer les données des équipes avec les détails de membre
        equipes_details = []
        for me in membre_equipes:
            # Récupérer les autres membres de l'équipe (jusqu'à 3 pour l'affichage)
            autres_membres = me.equipe.membres.exclude(utilisateur=request.user).select_related('utilisateur')[:3]
            total_membres = me.equipe.membres.count()
            
            # Créer un dictionnaire avec toutes les informations nécessaires
            equipe_detail = {
                'equipe': me.equipe,
                'position': me.position,
                'date_ajout': me.date_ajout,
                'autres_membres': autres_membres,
                'total_membres': total_membres,
                'nombre_tournois': me.equipe.inscriptions_tournois.count(),
            }
            equipes_details.append(equipe_detail)
        
        # Récupérer les matchs à venir des équipes du participant
        prochains_matchs = []
        now = timezone.now()
        
        # Récupérer les IDs des équipes du participant
        equipe_ids = [me.equipe.id for me in membre_equipes]
        
        if equipe_ids:
            # Matchs de tournoi à venir
            try:
                matchs_tournoi = MatchTournoi.objects.filter(
                    Q(equipe_domicile__id__in=equipe_ids) | Q(equipe_exterieur__id__in=equipe_ids),
                    date_match__gte=now
                ).select_related(
                    'equipe_domicile', 'equipe_exterieur', 'tournoi'
                ).order_by('date_match')[:10]
                
                for match in matchs_tournoi:
                    # Déterminer quelle est mon équipe et quelle est l'équipe adverse
                    is_domicile = match.equipe_domicile.id in equipe_ids
                    mon_equipe = match.equipe_domicile if is_domicile else match.equipe_exterieur
                    equipe_adverse = match.equipe_exterieur if is_domicile else match.equipe_domicile
                    
                    prochains_matchs.append({
                        'id': match.id,
                        'type': 'tournoi',
                        'mon_equipe': mon_equipe.nom,
                        'mon_equipe_id': mon_equipe.id,
                        'equipe_adverse': equipe_adverse.nom,
                        'equipe_adverse_id': equipe_adverse.id,
                        'tournoi': match.tournoi.nom,
                        'tournoi_id': match.tournoi.id,
                        'date': match.date_match,
                        'lieu': match.lieu_match if hasattr(match, 'lieu_match') else "À déterminer",
                        'url': f'/tournois/{match.tournoi.id}/',
                        'is_domicile': is_domicile,
                        'status': "À venir"
                    })
            except Exception as e:
                # Juste enregistrer l'erreur et continuer
                logger.error(f"Erreur lors du chargement des matchs de tournoi: {e}")
            
            # Matchs amicaux à venir
            try:
                matchs_amicaux = Match.objects.filter(
                    Q(equipe_a__id__in=equipe_ids) | Q(equipe_b__id__in=equipe_ids),
                    date__gte=now
                ).select_related(
                    'equipe_a', 'equipe_b'
                ).order_by('date')[:10]
                
                for match in matchs_amicaux:
                    # Déterminer quelle est mon équipe et quelle est l'équipe adverse
                    is_equipe_a = match.equipe_a.id in equipe_ids
                    mon_equipe = match.equipe_a if is_equipe_a else match.equipe_b
                    equipe_adverse = match.equipe_b if is_equipe_a else match.equipe_a
                    
                    prochains_matchs.append({
                        'id': match.id,
                        'type': 'amical',
                        'mon_equipe': mon_equipe.nom,
                        'mon_equipe_id': mon_equipe.id,
                        'equipe_adverse': equipe_adverse.nom,
                        'equipe_adverse_id': equipe_adverse.id,
                        'tournoi': "Match amical",
                        'tournoi_id': None,
                        'date': match.date,
                        'lieu': match.lieu if match.lieu else "À déterminer",
                        'url': f'/matchs/{match.id}/',
                        'is_domicile': is_equipe_a,
                        'status': "À venir"
                    })
            except Exception as e:
                # Juste enregistrer l'erreur et continuer
                logger.error(f"Erreur lors du chargement des matchs amicaux: {e}")
            
            # Trier tous les matchs par date (du plus proche au plus lointain)
            prochains_matchs = sorted(prochains_matchs, key=lambda m: m['date'])
            
            # Limiter aux 5 prochains matchs
            prochains_matchs = prochains_matchs[:5]
        
        context = {
            'equipes_details': equipes_details,
            'total_equipes': len(equipes_details),
            'prochains_matchs': prochains_matchs,
            'page_title': 'Mon Espace Participant',
            'breadcrumbs': [
                {'name': 'Accueil', 'url': 'home'},
                {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
            ]
        }

        return render(request, 'participants/tableau_bord.html', context)

    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la récupération de vos équipes : {str(e)}")
        return redirect('tournois:liste')

@login_required
def voir_calendrier_resultats_participant(request, equipe_id):
    """
    Vue pour un participant pour voir le calendrier et les résultats
    d'une équipe spécifique dont il est membre.
    """
    # Assurez-vous que l'utilisateur est bien un participant
    if request.user.type != 'participant':
        messages.error(request, "Accès réservé aux participants.", extra_tags='alert-danger')
        if request.user.type == 'responsable':
            return redirect('responsables:tableau_bord')
        elif request.user.type == 'organisateur':
            return redirect('organisateurs:dashboard')
        return redirect('home')

    # Vérifier que l'équipe existe et que l'utilisateur en est membre
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
    except:
        messages.error(request, "Cette équipe n'existe pas.", extra_tags='alert-danger')
        return redirect('participants:tableau_bord')

    if not MembreEquipe.objects.filter(equipe=equipe, utilisateur=request.user).exists():
        messages.error(request, "Vous ne faites pas partie de cette équipe.", extra_tags='alert-danger')
        return redirect('participants:tableau_bord')

    # Récupérer les matchs impliquant cette équipe (passés et futurs)
    matchs = MatchTournoi.objects.filter(
        Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe)
    ).order_by('date_match') # Ordonner par date

    # Séparer les matchs en futurs et terminés, et calculer les résultats pour les terminés
    prochains_matchs = []
    resultats_matchs = []
    now = timezone.now()

    for match in matchs:
        if match.date_match > now:
            prochains_matchs.append(match)
        else:
            # Calculer le résultat pour les matchs terminés
            resultat = ""
            score_equipe = None
            score_adversaire = None

            if match.termine and match.score_domicile is not None and match.score_exterieur is not None:
                 if match.equipe_domicile == equipe:
                    score_equipe = match.score_domicile
                    score_adversaire = match.score_exterieur
                    if match.score_domicile > match.score_exterieur:
                        resultat = "Victoire"
                    elif match.score_domicile == match.score_exterieur:
                        resultat = "Nul"
                    else:
                        resultat = "Défaite"
                 else: # equipe_exterieur == equipe
                    score_equipe = match.score_exterieur
                    score_adversaire = match.score_domicile
                    if match.score_exterieur > match.score_domicile:
                        resultat = "Victoire"
                    elif match.score_exterieur == match.score_domicile:
                        resultat = "Nul"
                    else:
                        resultat = "Défaite"

            resultats_matchs.append({
                'match': match,
                'resultat': resultat,
                'score_equipe': score_equipe,
                'score_adversaire': score_adversaire,
            })

    context = {
        'equipe': equipe,
        'prochains_matchs': prochains_matchs,
        'resultats_matchs': resultats_matchs,
        'now': now,
        'page_title': f'Calendrier & Résultats de {equipe.nom}',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
            {'name': equipe.nom, 'url': None},
            {'name': 'Matchs Tournoi', 'url': None, 'active': True}
        ]
    }

    return render(request, 'participants/voir_calendrier_resultats.html', context)

@login_required
def voir_matchs_amicaux(request, equipe_id):
    """
    Vue pour un participant pour voir les matchs amicaux
    d'une équipe spécifique dont il est membre.
    """
    # Assurez-vous que l'utilisateur est bien un participant
    if request.user.type != 'participant':
        messages.error(request, "Accès réservé aux participants.", extra_tags='alert-danger')
        if request.user.type == 'responsable':
            return redirect('responsables:tableau_bord')
        elif request.user.type == 'organisateur':
            return redirect('organisateurs:dashboard')
        return redirect('home')

    # Vérifier que l'équipe existe et que l'utilisateur en est membre
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
    except:
        messages.error(request, "Cette équipe n'existe pas.", extra_tags='alert-danger')
        return redirect('participants:tableau_bord')

    if not MembreEquipe.objects.filter(equipe=equipe, utilisateur=request.user).exists():
        messages.error(request, "Vous ne faites pas partie de cette équipe.", extra_tags='alert-danger')
        return redirect('participants:tableau_bord')

    # Récupérer les matchs amicaux impliquant cette équipe
    matchs = Match.objects.filter(
        Q(equipe_a=equipe) | Q(equipe_b=equipe)
    ).order_by('date')

    # Séparer les matchs en futurs et passés
    now = timezone.now()
    matchs_a_venir = matchs.filter(date__gt=now)
    matchs_passes = matchs.filter(date__lte=now)
    
    # Préparer les données des résultats pour les matchs passés
    resultats_matchs = []
    
    for match in matchs_passes:
        resultat = ""
        score_equipe = None
        score_adversaire = None
        
        if match.termine and match.score_equipe_a is not None and match.score_equipe_b is not None:
            if match.equipe_a == equipe:
                score_equipe = match.score_equipe_a
                score_adversaire = match.score_equipe_b
                if match.score_equipe_a > match.score_equipe_b:
                    resultat = "Victoire"
                elif match.score_equipe_a == match.score_equipe_b:
                    resultat = "Nul"
                else:
                    resultat = "Défaite"
            else:  # match.equipe_b == equipe
                score_equipe = match.score_equipe_b
                score_adversaire = match.score_equipe_a
                if match.score_equipe_b > match.score_equipe_a:
                    resultat = "Victoire"
                elif match.score_equipe_b == match.score_equipe_a:
                    resultat = "Nul"
                else:
                    resultat = "Défaite"
        
        resultats_matchs.append({
            'match': match,
            'resultat': resultat,
            'score_equipe': score_equipe,
            'score_adversaire': score_adversaire,
        })
    
    context = {
        'equipe': equipe,
        'matchs_a_venir': matchs_a_venir,
        'resultats_matchs': resultats_matchs,
        'now': now,
        'page_title': f'Matchs Amicaux - {equipe.nom}',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
            {'name': equipe.nom, 'url': 'participants:voir_calendrier_resultats_participant', 'equipe_id': equipe.id},
            {'name': 'Matchs Amicaux', 'url': None, 'active': True}
        ]
    }
    
    return render(request, 'participants/voir_matchs_amicaux.html', context)

@login_required
def voir_tournois_disponibles(request):
    """
    Vue pour un participant pour voir la liste des tournois disponibles
    """
    # Assurez-vous que l'utilisateur est bien un participant
    if request.user.type != 'participant':
        messages.error(request, "Accès réservé aux participants.", extra_tags='alert-danger')
        if request.user.type == 'responsable':
            return redirect('responsables:tableau_bord')
        elif request.user.type == 'organisateur':
            return redirect('organisateurs:dashboard')
        return redirect('home')

    # Récupérer les équipes auxquelles le participant appartient
    equipes_membre = Equipe.objects.filter(membres__utilisateur=request.user)
    
    # Récupérer tous les tournois en cours ou à venir
    aujourd_hui = timezone.now().date()
    tournois = Tournoi.objects.filter(Q(date_debut__gte=aujourd_hui) | 
                                      Q(date_fin__isnull=True) | 
                                      Q(date_fin__gte=aujourd_hui)).order_by('date_debut')
    
    # Préparer les informations à afficher pour chaque tournoi
    tournois_info = []
    for tournoi in tournois:
        # Vérifier si une des équipes du participant est déjà inscrite
        inscriptions = InscriptionTournoi.objects.filter(tournoi=tournoi, equipe__in=equipes_membre)
        equipes_inscrites = [inscription.equipe for inscription in inscriptions]
        
        tournoi_info = {
            'tournoi': tournoi,
            'equipes_inscrites': equipes_inscrites,
            'est_inscrit': len(equipes_inscrites) > 0
        }
        tournois_info.append(tournoi_info)
    
    context = {
        'tournois_info': tournois_info,
        'equipes_membre': equipes_membre,
        'page_title': 'Tournois Disponibles',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
            {'name': 'Tournois Disponibles', 'url': None, 'active': True}
        ]
    }
    
    return render(request, 'participants/voir_tournois_disponibles.html', context)

@participant_required
def mes_equipes_view(request):
    """Vue pour afficher toutes les équipes dont l'utilisateur est membre"""
    try:
        # Récupérer les équipes avec plus de détails
        mes_equipes = MembreEquipe.objects.filter(
            utilisateur=request.user
        ).select_related(
            'equipe', 
            'equipe__responsable', 
            'equipe__responsable__user'
        )
        
        context = {
            'mes_equipes': mes_equipes,
            'page_title': 'Mes équipes',
            'breadcrumbs': [
                {'name': 'Accueil', 'url': 'home'},
                {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
                {'name': 'Mes Équipes', 'url': None, 'active': True}
            ]
        }
        
        return render(request, 'participants/mes_equipes.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}")
        return redirect('participants:tableau_bord')

@participant_required
def mes_matchs_view(request):
    """Vue pour afficher tous les matchs des équipes du participant"""
    try:
        # Récupérer les équipes du participant
        equipe_ids = MembreEquipe.objects.filter(
            utilisateur=request.user
        ).values_list('equipe_id', flat=True)
        
        # Récupérer tous les matchs (tournoi et amicaux)
        now = timezone.now()
        
        # Matchs à venir
        matchs_a_venir = []
        
        # Matchs de tournoi à venir
        matchs_tournoi_a_venir = MatchTournoi.objects.filter(
            (Q(equipe_domicile__id__in=equipe_ids) | Q(equipe_exterieur__id__in=equipe_ids)) &
            Q(date_match__gt=now)
        ).select_related('equipe_domicile', 'equipe_exterieur', 'tournoi').order_by('date_match')
        
        for match in matchs_tournoi_a_venir:
            matchs_a_venir.append({
                'id': match.id,
                'equipe_a': match.equipe_domicile,
                'equipe_b': match.equipe_exterieur,
                'date': match.date_match,
                'lieu': match.lieu or "À définir",
                'type': 'tournoi',
                'tournoi': match.tournoi.nom if match.tournoi else "Tournoi",
                'url': f"/tournois/match/{match.id}/"
            })
        
        # Matchs amicaux à venir
        matchs_amicaux_a_venir = Match.objects.filter(
            (Q(equipe_a__id__in=equipe_ids) | Q(equipe_b__id__in=equipe_ids)) &
            Q(date__gt=now)
        ).select_related('equipe_a', 'equipe_b').order_by('date')
        
        for match in matchs_amicaux_a_venir:
            matchs_a_venir.append({
                'id': match.id,
                'equipe_a': match.equipe_a,
                'equipe_b': match.equipe_b,
                'date': match.date,
                'lieu': match.lieu or "À définir",
                'type': 'amical',
                'tournoi': None,
                'url': f"/matchs/{match.id}/"
            })
            
        # Trier tous les matchs par date
        matchs_a_venir.sort(key=lambda m: m['date'])
        
        # Matchs passés
        matchs_passes = []
        
        # Matchs de tournoi passés
        matchs_tournoi_passes = MatchTournoi.objects.filter(
            (Q(equipe_domicile__id__in=equipe_ids) | Q(equipe_exterieur__id__in=equipe_ids)) &
            Q(date_match__lte=now)
        ).select_related('equipe_domicile', 'equipe_exterieur', 'tournoi').order_by('-date_match')
        
        for match in matchs_tournoi_passes:
            # Calculer le résultat du match
            resultat = "Non joué"
            mon_equipe = None
            adversaire = None
            
            if match.equipe_domicile.id in equipe_ids:
                mon_equipe = match.equipe_domicile
                adversaire = match.equipe_exterieur
                score_mon_equipe = match.score_domicile
                score_adversaire = match.score_exterieur
            else:
                mon_equipe = match.equipe_exterieur
                adversaire = match.equipe_domicile
                score_mon_equipe = match.score_exterieur
                score_adversaire = match.score_domicile
            
            if match.termine and score_mon_equipe is not None and score_adversaire is not None:
                if score_mon_equipe > score_adversaire:
                    resultat = "Victoire"
                elif score_mon_equipe < score_adversaire:
                    resultat = "Défaite"
                else:
                    resultat = "Match nul"
            
            matchs_passes.append({
                'id': match.id,
                'mon_equipe': mon_equipe,
                'adversaire': adversaire,
                'date': match.date_match,
                'lieu': match.lieu or "Non défini",
                'type': 'tournoi',
                'tournoi': match.tournoi.nom if match.tournoi else "Tournoi",
                'resultat': resultat,
                'score_mon_equipe': score_mon_equipe,
                'score_adversaire': score_adversaire,
                'url': f"/tournois/match/{match.id}/"
            })
        
        # Matchs amicaux passés
        matchs_amicaux_passes = Match.objects.filter(
            (Q(equipe_a__id__in=equipe_ids) | Q(equipe_b__id__in=equipe_ids)) &
            Q(date__lte=now)
        ).select_related('equipe_a', 'equipe_b').order_by('-date')
        
        for match in matchs_amicaux_passes:
            # Calculer le résultat du match
            resultat = "Non joué"
            mon_equipe = None
            adversaire = None
            
            if match.equipe_a.id in equipe_ids:
                mon_equipe = match.equipe_a
                adversaire = match.equipe_b
                score_mon_equipe = match.score_equipe_a
                score_adversaire = match.score_equipe_b
            else:
                mon_equipe = match.equipe_b
                adversaire = match.equipe_a
                score_mon_equipe = match.score_equipe_b
                score_adversaire = match.score_equipe_a
            
            if match.termine and score_mon_equipe is not None and score_adversaire is not None:
                if score_mon_equipe > score_adversaire:
                    resultat = "Victoire"
                elif score_mon_equipe < score_adversaire:
                    resultat = "Défaite"
                else:
                    resultat = "Match nul"
            
            matchs_passes.append({
                'id': match.id,
                'mon_equipe': mon_equipe,
                'adversaire': adversaire,
                'date': match.date,
                'lieu': match.lieu or "Non défini",
                'type': 'amical',
                'tournoi': None,
                'resultat': resultat,
                'score_mon_equipe': score_mon_equipe,
                'score_adversaire': score_adversaire,
                'url': f"/matchs/{match.id}/"
            })
        
        # Trier tous les matchs passés par date (les plus récents d'abord)
        matchs_passes.sort(key=lambda m: m['date'], reverse=True)
        
        context = {
            'matchs_a_venir': matchs_a_venir,
            'matchs_passes': matchs_passes,
            'page_title': 'Mes matchs',
            'breadcrumbs': [
                {'name': 'Accueil', 'url': 'home'},
                {'name': 'Mon Espace', 'url': 'participants:tableau_bord'},
                {'name': 'Mes Matchs', 'url': None, 'active': True}
            ]
        }
        
        return render(request, 'participants/mes_matchs.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}")
        return redirect('participants:tableau_bord')
