# responsables/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from equipes.models import Equipe, MembreEquipe
from equipes.forms import MembreEquipeForm, AjoutMembreEmailForm
from accounts.models import CustomUser
from .models import Responsable
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.db import transaction
from tournois.models import MatchTournoi, Tournoi, InscriptionTournoi # Correction: utiliser InscriptionTournoi au lieu de Participation
import logging
from matchs.models import Match

# Configuration du logger
logger = logging.getLogger(__name__)

def get_equipe_responsable(user):
    """Fonction utilitaire pour récupérer l'équipe d'un responsable"""
    logger.debug(f"Attempting to get team for user: {user.username}")
    try:
        # Essayer de récupérer le profil responsable existant
        try:
            responsable = Responsable.objects.get(user=user)
        except Responsable.DoesNotExist:
            # Si le profil n'existe pas et que l'utilisateur est de type responsable, le créer
            if user.type == 'responsable':
                logger.info(f"Creating new Responsable profile for user: {user.username}")
                responsable = Responsable.objects.create(user=user)
            else:
                logger.warning(f"Responsable profile not found for user: {user.username}")
                return None

        logger.debug(f"Found Responsable profile for user {user.username}: {responsable}")
        # Utiliser select_related pour éviter N+1 query si vous accédez à equipe.membres plus tard
        try:
            equipe = Equipe.objects.get(responsable=responsable)
            logger.debug(f"Found team for user {user.username}: {equipe.nom}")
            return equipe
        except Equipe.DoesNotExist:
            logger.warning(f"Equipe not found for responsible user: {user.username}")
            return None
    except Exception as e:
        logger.error(f"Error in get_equipe_responsable for user {user.username}: {e}")
        return None

@login_required
def tableau_bord_responsable(request):
    """
    Vue principale du tableau de bord pour les responsables d'équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    # Initialiser le contexte avec des valeurs par défaut
    context = {
        'has_equipe': False,
        'membres_count': 0,
        'membres_percent': 0,
        'upcoming_count': 0,
        'past_count': 0,
        'prochains_matchs': [],
        'derniers_matchs': [],
        'victoires': 0,
        'nuls': 0,
        'defaites': 0,
        'buts_marques': 0,
        'tournois_inscrits': [],
        'tournois_disponibles': [],
        'matchs_amicaux_a_venir': [],
        'matchs_amicaux_passes': []
    }
    
    try:
        # Vérifier si l'utilisateur a une équipe
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            context['has_equipe'] = False
            return render(request, 'responsables/tableau_bord.html', context)
            
        has_equipe = True
        
        # Récupérer les membres de l'équipe
        membres = MembreEquipe.objects.filter(equipe=equipe).select_related('utilisateur')
        membres_count = membres.count()
        membres_percent = min(int((membres_count / 20) * 100), 100)
        
        # Importer le modèle de match depuis tournois
        from tournois.models import MatchTournoi
        
        # Récupérer les prochains matchs
        prochains_matchs = MatchTournoi.objects.filter(
            Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe),
            date_match__gt=timezone.now()
        ).order_by('date_match')[:5]
        
        # Récupérer les derniers matchs
        derniers_matchs = MatchTournoi.objects.filter(
            Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe),
            date_match__lte=timezone.now()
        ).order_by('-date_match')[:5]
        
        # Récupérer les matchs amicaux
        from matchs.models import Match
        matchs_amicaux = Match.objects.filter(
            Q(equipe_a=equipe) | Q(equipe_b=equipe),
            tournoi__isnull=True  # Matchs sans tournoi associé = amicaux
        )
        
        # Séparer les matchs amicaux à venir et passés
        matchs_amicaux_a_venir = matchs_amicaux.filter(
            date__gt=timezone.now()
        ).order_by('date')[:3]
        
        matchs_amicaux_passes = matchs_amicaux.filter(
            date__lte=timezone.now()
        ).order_by('-date')[:3]
        
        # Calculer les statistiques
        matchs_termines = MatchTournoi.objects.filter(
            Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe),
            termine=True
        )
        
        victoires = 0
        nuls = 0
        defaites = 0
        buts_marques = 0
        
        for match in matchs_termines:
            if match.equipe_domicile == equipe:
                buts_marques += match.score_domicile or 0
                if match.score_domicile > match.score_exterieur:
                    victoires += 1
                elif match.score_domicile == match.score_exterieur:
                    nuls += 1
                else:
                    defaites += 1
            else:  # equipe_exterieur
                buts_marques += match.score_exterieur or 0
                if match.score_exterieur > match.score_domicile:
                    victoires += 1
                elif match.score_exterieur == match.score_domicile:
                    nuls += 1
                else:
                    defaites += 1
        
        # Calculer les résultats pour les derniers matchs à afficher dans le tableau de bord
        derniers_matchs_avec_resultat = []
        for match in derniers_matchs:
            resultat = ""
            if match.termine and match.score_domicile is not None and match.score_exterieur is not None:
                if match.equipe_domicile == equipe:
                    if match.score_domicile > match.score_exterieur:
                        resultat = "victoire"
                    elif match.score_domicile == match.score_exterieur:
                        resultat = "nul"
                    else:
                        resultat = "defaite"
                else: # equipe_exterieur == equipe
                    if match.score_exterieur > match.score_domicile:
                        resultat = "victoire"
                    elif match.score_exterieur == match.score_domicile:
                        resultat = "nul"
                    else:
                        resultat = "defaite"
            
            derniers_matchs_avec_resultat.append({
                'match': match,
                'resultat': resultat,
                'score_equipe': match.score_domicile if match.equipe_domicile == equipe else match.score_exterieur,
                'score_adversaire': match.score_exterieur if match.equipe_domicile == equipe else match.score_domicile,
            })
        
        # Récupérer les tournois pour le tableau de bord
        # Récupérer tous les tournois actifs et à venir (limité à 3 pour le tableau de bord)
        tournois_actifs = Tournoi.objects.filter(
            date_fin__gte=timezone.now()
        ).order_by('date_debut')
        
        # Récupérer les tournois auxquels l'équipe participe déjà
        tournois_inscrits_ids = InscriptionTournoi.objects.filter(
            equipe=equipe
        ).values_list('tournoi_id', flat=True)
        
        # Filtrer les tournois non inscrits pour l'équipe
        tournois_disponibles = tournois_actifs.exclude(id__in=tournois_inscrits_ids)[:3]
        tournois_inscrits = tournois_actifs.filter(id__in=tournois_inscrits_ids)[:3]
        
        # Mise à jour du contexte
        context.update({
            'equipe': equipe,
            'has_equipe': has_equipe,
            'membres': membres,
            'membres_count': membres_count,
            'membres_percent': membres_percent,
            'upcoming_count': prochains_matchs.count(),
            'past_count': derniers_matchs.count(),
            'prochains_matchs': prochains_matchs,
            'derniers_matchs': derniers_matchs_avec_resultat,
            'victoires': victoires,
            'nuls': nuls,
            'defaites': defaites,
            'buts_marques': buts_marques,
            'tournois_inscrits': tournois_inscrits,
            'tournois_disponibles': tournois_disponibles,
            'matchs_amicaux_a_venir': matchs_amicaux_a_venir,
            'matchs_amicaux_passes': matchs_amicaux_passes
        })
        
    except Exception as e:
        print(f"DEBUG - Erreur pendant le traitement des données: {str(e)}")
        messages.error(
            request, 
            f"Une erreur s'est produite lors du chargement du tableau de bord: {str(e)}", 
            extra_tags='alert-danger'
        )
    
    return render(request, 'responsables/tableau_bord.html', context)

@login_required
def gestion_membres(request):
    """
    Vue pour la gestion des membres de l'équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Vérifier si l'utilisateur a une équipe
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous devez d'abord créer une équipe", extra_tags='alert-warning')
            return redirect('equipes:gestion_equipe')
            
        membres = MembreEquipe.objects.filter(equipe=equipe).select_related('utilisateur').order_by('position', 'date_ajout')
        
        # Traitement du formulaire d'ajout de membre
        if request.method == 'POST':
            form = MembreEquipeForm(request.POST, equipe=equipe)
            if form.is_valid():
                membre = form.save(commit=False)
                membre.equipe = equipe
                membre.save()
                
                nom_utilisateur = membre.utilisateur.get_full_name() or membre.utilisateur.username
                messages.success(
                    request, 
                    f"{nom_utilisateur} a été ajouté à votre équipe avec succès", 
                    extra_tags='alert-success'
                )
                return redirect('responsables:gestion_membres')
        else:
            form = MembreEquipeForm(equipe=equipe)
            
        context = {
            'equipe': equipe,
            'membres': membres,
            'form': form,
            'peut_ajouter': equipe.peut_ajouter_membre() if hasattr(equipe, 'peut_ajouter_membre') else membres.count() < 20
        }
        
        return render(request, 'responsables/gestion_membres.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue: {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:tableau_bord')

@login_required
def supprimer_membre(request, membre_id):
    """
    Vue pour supprimer un membre d'une équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Vérifier que l'utilisateur a une équipe
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous n'avez pas d'équipe", extra_tags='alert-danger')
            return redirect('equipes:gestion_equipe')
            
        # Récupérer le membre à supprimer et vérifier qu'il appartient à cette équipe
        membre = get_object_or_404(MembreEquipe, id=membre_id, equipe=equipe)
        
        # Récupérer le nom pour le message de confirmation
        nom_utilisateur = membre.utilisateur.get_full_name() or membre.utilisateur.username
        
        # Supprimer le membre
        membre.delete()
        
        messages.success(
            request, 
            f"{nom_utilisateur} a été retiré de votre équipe avec succès", 
            extra_tags='alert-success'
        )
        
    except MembreEquipe.DoesNotExist:
        messages.error(
            request, 
            "Ce membre n'existe pas ou ne fait pas partie de votre équipe", 
            extra_tags='alert-danger'
        )
    except Exception as e:
        messages.error(
            request, 
            f"Une erreur est survenue lors de la suppression : {str(e)}", 
            extra_tags='alert-danger'
        )
    
    return redirect('responsables:gestion_membres')

@login_required
def modifier_membre(request, membre_id):
    """
    Vue pour modifier les informations d'un membre d'une équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Vérifier que l'utilisateur a une équipe
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous n'avez pas d'équipe", extra_tags='alert-danger')
            return redirect('equipes:gestion_equipe')
            
        # Récupérer le membre à modifier et vérifier qu'il appartient à cette équipe
        membre = get_object_or_404(MembreEquipe, id=membre_id, equipe=equipe)
        
        if request.method == 'POST':
            # Récupérer la nouvelle position
            position = request.POST.get('position', '')
            
            # Mettre à jour la position
            membre.position = position
            membre.save()
            
            nom_utilisateur = membre.utilisateur.get_full_name() or membre.utilisateur.username
            messages.success(
                request, 
                f"Les informations de {nom_utilisateur} ont été mises à jour avec succès", 
                extra_tags='alert-success'
            )
            
            return redirect('responsables:gestion_membres')
            
        # Pour les requêtes GET, afficher le formulaire de modification
        positions_choices = MembreEquipe.POSITIONS_CHOICES
        
        context = {
            'membre': membre,
            'equipe': equipe,
            'positions_choices': positions_choices
        }
        
        return render(request, 'responsables/modifier_membre.html', context)
        
    except MembreEquipe.DoesNotExist:
        messages.error(
            request, 
            "Ce membre n'existe pas ou ne fait pas partie de votre équipe", 
            extra_tags='alert-danger'
        )
        return redirect('responsables:gestion_membres')
    except Exception as e:
        messages.error(
            request, 
            f"Une erreur est survenue : {str(e)}", 
            extra_tags='alert-danger'
        )
        return redirect('responsables:gestion_membres')

@login_required
def voir_matches(request):
    """
    Vue pour voir les matchs à venir de l'équipe du responsable.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous devez d'abord créer une équipe", extra_tags='alert-warning')
            return redirect('equipes:gestion_equipe')
        
        # Importer le modèle de match depuis tournois
        from tournois.models import MatchTournoi
        
        # Récupérer les matchs à venir
        matchs_a_venir = MatchTournoi.objects.filter(
            Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe),
            date_match__gt=timezone.now()
        )
        
        # Appliquer les filtres
        tri = request.GET.get('tri')
        if tri == 'date':
            matchs_a_venir = matchs_a_venir.order_by('date_match')
        elif tri == 'domicile':
            matchs_a_venir = matchs_a_venir.filter(equipe_domicile=equipe)
        elif tri == 'exterieur':
            matchs_a_venir = matchs_a_venir.filter(equipe_exterieur=equipe)
        # Pour le filtre par tournoi, cela nécessiterait une logique plus complexe (jointure/annotation)
        
        # Séparer par statut (appliquer après le filtrage)
        matchs_confirmes = matchs_a_venir.filter(tournoi__isnull=False)
        matchs_amicaux = matchs_a_venir.filter(tournoi__isnull=True)
        
        context = {
            'equipe': equipe,
            'matchs_confirmes': matchs_confirmes,
            'matchs_amicaux': matchs_amicaux,
            'total_matchs': matchs_a_venir.count(),
            'now': timezone.now()  # Ajout de la date actuelle pour les comparaisons
        }
        
        return render(request, 'responsables/voir_matches.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:tableau_bord')

@login_required
def voir_resultats(request):
    """
    Vue pour le responsable pour voir les résultats des matchs de son équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')

    equipe = get_equipe_responsable(request.user)

    if not equipe:
        messages.error(request, "Vous devez d'abord créer une équipe pour voir les résultats.", extra_tags='alert-warning')
        return redirect('equipes:gestion_equipe') # Rediriger vers la page de gestion/création d'équipe

    # Récupérer tous les matchs terminés impliquant l'équipe
    matchs_termines = MatchTournoi.objects.filter(
        Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe),
        termine=True # Assurez-vous que 'termine' est un champ booléen sur votre modèle MatchTournoi
    ).order_by('-date_match') # Afficher les plus récents en premier

    # Préparer les données des matchs avec le résultat calculé
    resultats_matchs = []
    for match in matchs_termines:
        resultat = ""
        score_equipe = None
        score_adversaire = None

        if match.score_domicile is not None and match.score_exterieur is not None:
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
        'resultats_matchs': resultats_matchs,
        'page_title': 'Résultats de l\'équipe',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Tableau de Bord Responsable', 'url': 'responsables:tableau_bord'},
            {'name': 'Résultats', 'url': 'responsables:voir_resultats'},
        ]
    }

    return render(request, 'responsables/voir_resultats.html', context)

@login_required
def ajouter_membre(request, equipe_id=None):
    """
    Vue pour ajouter un membre à une équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Déterminer l'équipe
        equipe = get_equipe_responsable(request.user)
        
        # Si pas d'équipe, rediriger vers la page de gestion
        if not equipe:
            messages.error(request, "Vous devez d'abord créer une équipe pour ajouter des membres.", extra_tags='alert-warning')
            return redirect('equipes:gestion_equipe')  # Redirection vers la gestion d'équipe
            
        # Vérifier si l'équipe peut accueillir de nouveaux membres
        if equipe.nombre_membres() >= 20:
            messages.error(request, "Votre équipe a atteint la limite de 20 membres", extra_tags='alert-warning')
            return redirect('responsables:gestion_membres')
        
        if request.method == 'POST':
            email = request.POST.get('email', '').strip()
            
            if not email:
                messages.error(request, "Veuillez saisir un email", extra_tags='alert-warning')
            else:
                try:
                    utilisateur = CustomUser.objects.get(email=email)
                    
                    # Vérifier que l'utilisateur n'est pas déjà membre de cette équipe
                    if MembreEquipe.objects.filter(equipe=equipe, utilisateur=utilisateur).exists():
                        messages.error(request, "Cet utilisateur est déjà membre de l'équipe", extra_tags='alert-warning')
                    else:
                        # Rediriger vers la sélection de position
                        return redirect('responsables:selectionner_position', equipe_id=equipe.id, utilisateur_id=utilisateur.id)
                        
                except CustomUser.DoesNotExist:
                    messages.error(request, "Aucun utilisateur trouvé avec cet email", extra_tags='alert-warning')
        
        context = {
            'equipe': equipe,
            'membres_actuels': equipe.nombre_membres(),
            'peut_ajouter': equipe.nombre_membres() < 20
        }
        
        return render(request, 'responsables/ajouter_membre.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:gestion_membres')

@login_required
def rechercher_utilisateur(request):
    """
    Vue pour rechercher un utilisateur à ajouter à l'équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    if request.method == 'POST':
        search_term = request.POST.get('search_term', '').strip()
        equipe_id = request.POST.get('equipe_id')
        
        if not search_term:
            messages.error(request, "Veuillez saisir un terme de recherche", extra_tags='alert-warning')
            return redirect('responsables:ajouter_membre')
        
        try:
            equipe = get_object_or_404(Equipe, id=equipe_id)
            
            # Vérifier que l'utilisateur est le responsable de cette équipe
            if equipe.responsable != request.user:
                messages.error(request, "Vous n'êtes pas autorisé à gérer cette équipe", extra_tags='alert-danger')
                return redirect('responsables:tableau_bord')
            
            # Rechercher les utilisateurs
            search_results = CustomUser.objects.filter(
                Q(email__icontains=search_term) | 
                Q(username__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term),
                type='invite'  # Seuls les invités peuvent être ajoutés
            ).exclude(
                id__in=MembreEquipe.objects.filter(equipe=equipe).values_list('utilisateur_id', flat=True)
            )
            
            context = {
                'equipe': equipe,
                'search_results': search_results,
                'search_performed': True,
                'search_term': search_term
            }
            
            return render(request, 'responsables/ajouter_membre.html', context)
            
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
    
    return redirect('responsables:ajouter_membre')

@login_required
def selectionner_position(request, equipe_id, utilisateur_id):
    """
    Vue pour sélectionner la position d'un nouveau membre.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
        utilisateur = get_object_or_404(CustomUser, id=utilisateur_id)
        
        # Vérifier que l'utilisateur est le responsable de cette équipe
        if not equipe.responsable or equipe.responsable.user != request.user:
            messages.error(request, "Vous n'êtes pas autorisé à gérer cette équipe", extra_tags='alert-danger')
            return redirect('responsables:tableau_bord')
        
        # Vérifier que l'utilisateur n'est pas déjà membre
        if MembreEquipe.objects.filter(equipe=equipe, utilisateur=utilisateur).exists():
            messages.error(request, "Cet utilisateur est déjà membre de l'équipe", extra_tags='alert-warning')
            return redirect('responsables:gestion_membres')
        
        # Si la méthode est POST, c'est un formulaire de sélection de position soumis
        if request.method == 'POST':
            position = request.POST.get('position', '')
            
            # Créer le membre directement
            membre = MembreEquipe.objects.create(
                equipe=equipe,
                utilisateur=utilisateur,
                position=position,
                is_new=True
            )
            
            nom_utilisateur = utilisateur.get_full_name() or utilisateur.username
            messages.success(
                request, 
                f"{nom_utilisateur} a été ajouté à votre équipe avec succès", 
                extra_tags='alert-success'
            )
            
            # Si l'utilisateur est de type invite, le changer en participant
            if utilisateur.type == 'invite':
                utilisateur.type = 'participant'
                utilisateur.save()
                logger.info(f"Utilisateur {utilisateur.username} changé de type invite à participant")
            
            return redirect('responsables:tableau_bord')
        
        positions_choices = [
            ('', 'Non définie'),
            ('Gardien', 'Gardien'),
            ('Défenseur', 'Défenseur'),
            ('Milieu', 'Milieu de terrain'),
            ('Attaquant', 'Attaquant'),
            ('Entraîneur', 'Entraîneur'),
            ('Remplaçant', 'Remplaçant'),
        ]
        
        context = {
            'equipe': equipe,
            'utilisateur': utilisateur,
            'positions_choices': positions_choices
        }
        
        return render(request, 'responsables/selectionner_position.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:gestion_membres')

@login_required
def confirmer_ajout(request, equipe_id, utilisateur_id):
    """
    Vue pour confirmer l'ajout d'un membre avec sa position.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
        utilisateur = get_object_or_404(CustomUser, id=utilisateur_id)
        
        # Vérifier que l'utilisateur est le responsable de cette équipe
        if not equipe.responsable or equipe.responsable.user != request.user:
            messages.error(request, "Vous n'êtes pas autorisé à gérer cette équipe", extra_tags='alert-danger')
            return redirect('responsables:tableau_bord')
        
        # Vérifier que l'utilisateur n'est pas déjà membre
        if MembreEquipe.objects.filter(equipe=equipe, utilisateur=utilisateur).exists():
            messages.error(request, "Cet utilisateur est déjà membre de l'équipe", extra_tags='alert-warning')
            return redirect('responsables:gestion_membres')
        
        if request.method == 'POST':
            position = request.POST.get('position', '')
            
            context = {
                'equipe': equipe,
                'utilisateur': utilisateur,
                'position': position
            }
            
            return render(request, 'responsables/confirmer_ajout.html', context)
        
        return redirect('responsables:selectionner_position', equipe_id=equipe_id, utilisateur_id=utilisateur_id)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:gestion_membres')

@login_required
def finaliser_ajout(request, equipe_id, utilisateur_id):
    """
    Vue pour finaliser l'ajout d'un membre à l'équipe.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
        utilisateur = get_object_or_404(CustomUser, id=utilisateur_id)
        
        # Vérifier que l'utilisateur est le responsable de cette équipe
        if not equipe.responsable or equipe.responsable.user != request.user:
            messages.error(request, "Vous n'êtes pas autorisé à gérer cette équipe", extra_tags='alert-danger')
            return redirect('responsables:tableau_bord')
        
        # Vérifier que l'utilisateur n'est pas déjà membre
        if MembreEquipe.objects.filter(equipe=equipe, utilisateur=utilisateur).exists():
            messages.error(request, "Cet utilisateur est déjà membre de l'équipe", extra_tags='alert-warning')
            return redirect('responsables:gestion_membres')
        
        if request.method == 'POST':
            position = request.POST.get('position', '')
            
            # Créer le membre
            membre = MembreEquipe.objects.create(
                equipe=equipe,
                utilisateur=utilisateur,
                position=position,
                is_new=True
            )
            
            # Si l'utilisateur est de type invite, le changer en participant
            if utilisateur.type == 'invite':
                utilisateur.type = 'participant'
                utilisateur.save()
                logger.info(f"Utilisateur {utilisateur.username} changé de type invite à participant")
            
            nom_utilisateur = utilisateur.get_full_name() or utilisateur.username
            messages.success(
                request, 
                f"{nom_utilisateur} a été ajouté à votre équipe avec succès", 
                extra_tags='alert-success'
            )
            
            return redirect('responsables:gestion_membres')
        
        return redirect('responsables:selectionner_position', equipe_id=equipe_id, utilisateur_id=utilisateur_id)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:gestion_membres')

@login_required
def ajouter_membre_email(request):
    """
    Vue pour ajouter un membre à l'équipe par email.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous devez d'abord créer une équipe", extra_tags='alert-warning')
            return redirect('equipes:gestion_equipe')
        
        if request.method == 'POST':
            form = AjoutMembreEmailForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                position = form.cleaned_data['position']
                
                # Vérifier si l'utilisateur existe déjà
                existing_user = CustomUser.objects.filter(email=email).first()
                
                if existing_user:
                    # Vérifier si l'utilisateur est déjà membre de l'équipe
                    if MembreEquipe.objects.filter(equipe=equipe, utilisateur=existing_user).exists():
                        messages.error(
                            request, 
                            "Cet utilisateur est déjà membre de l'équipe", 
                            extra_tags='alert-warning'
                        )
                        return redirect('responsables:tableau_bord')
                    
                    # Ajouter directement l'utilisateur existant à l'équipe si c'est un participant
                    membre = MembreEquipe.objects.create(
                        equipe=equipe,
                        utilisateur=existing_user,
                        position=position,
                        is_new=True
                    )
                    
                    # Si l'utilisateur est de type invite, le changer en participant
                    if existing_user.type == 'invite':
                        existing_user.type = 'participant'
                        existing_user.save()
                        logger.info(f"Utilisateur existant {existing_user.username} changé de type invite à participant")
                    
                    messages.success(
                        request,
                        f"{existing_user.username} a été ajouté à votre équipe avec succès.",
                        extra_tags='alert-success'
                    )
                    return redirect('responsables:tableau_bord')
                
                # Si l'utilisateur n'existe pas, créer un nouvel utilisateur
                # Générer un mot de passe temporaire
                temp_password = get_random_string(12)
                
                # Créer un nouvel utilisateur
                username = email.split('@')[0]  # Utiliser la partie avant @ comme username
                base_username = username
                counter = 1
                
                # S'assurer que le username est unique
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=temp_password,
                    type='participant',  # Directement créer comme participant
                    is_active=True
                )
                
                # Créer le membre d'équipe
                membre = MembreEquipe.objects.create(
                    equipe=equipe,
                    utilisateur=user,
                    position=position,
                    is_new=True
                )
                
                # Préparer le contexte pour l'email
                context = {
                    'equipe': equipe,
                    'username': username,
                    'password': temp_password,
                    'login_url': request.build_absolute_uri(reverse('login')),
                    'equipe_url': request.build_absolute_uri(reverse('equipes:detail_equipe', args=[equipe.id]))
                }
                
                # Envoyer l'email d'invitation
                subject = f"Invitation à rejoindre l'équipe {equipe.nom}"
                html_message = render_to_string('responsables/email_invitation_membre.html', context)
                plain_message = f"""
                Bonjour,
                
                Vous avez été invité à rejoindre l'équipe {equipe.nom}.
                
                Vos identifiants de connexion sont :
                - Nom d'utilisateur : {username}
                - Mot de passe : {temp_password}
                
                Vous pouvez vous connecter ici : {context['login_url']}
                
                Une fois connecté, n'oubliez pas de changer votre mot de passe.
                
                Cordialement,
                L'équipe de gestion des tournois
                """
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message
                )
                
                messages.success(
                    request,
                    f"Une invitation a été envoyée à {email}. L'utilisateur pourra se connecter avec les identifiants envoyés par email.",
                    extra_tags='alert-success'
                )
                return redirect('responsables:tableau_bord')
        else:
            form = AjoutMembreEmailForm()
        
        context = {
            'form': form,
            'equipe': equipe
        }
        return render(request, 'responsables/ajouter_membre_email.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:tableau_bord')

@login_required
def voir_tournois(request):
    """
    Vue pour permettre aux responsables d'équipe de voir les tournois disponibles.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe", extra_tags='alert-danger')
        return redirect('home')
    
    try:
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.warning(request, "Vous devez d'abord créer une équipe pour voir les tournois disponibles", extra_tags='alert-warning')
            return redirect('equipes:gestion_equipe')
        
        # Récupérer tous les tournois actifs et à venir
        tournois_actifs = Tournoi.objects.filter(
            date_fin__gte=timezone.now()
        ).order_by('date_debut')
        
        # Récupérer les tournois auxquels l'équipe participe déjà
        tournois_inscrits_ids = InscriptionTournoi.objects.filter(
            equipe=equipe
        ).values_list('tournoi_id', flat=True)
        
        # Filtrer les tournois non inscrits pour l'équipe
        tournois_disponibles = tournois_actifs.exclude(id__in=tournois_inscrits_ids)
        tournois_inscrits = tournois_actifs.filter(id__in=tournois_inscrits_ids)
        
        # Enrichir les tournois avec le nombre d'équipes inscrites
        for tournoi in tournois_disponibles:
            tournoi.nombre_equipes = InscriptionTournoi.objects.filter(tournoi=tournoi).count()
            tournoi.capacite_equipes = tournoi.nombre_equipes_max
            
        for tournoi in tournois_inscrits:
            tournoi.nombre_equipes = InscriptionTournoi.objects.filter(tournoi=tournoi).count()
            tournoi.capacite_equipes = tournoi.nombre_equipes_max
        
        context = {
            'equipe': equipe,
            'tournois_disponibles': tournois_disponibles,
            'tournois_inscrits': tournois_inscrits,
            'page_title': 'Tournois disponibles',
            'now': timezone.now().date(),  # Convertir en date pour comparaison dans le template
            'breadcrumbs': [
                {'name': 'Accueil', 'url': 'home'},
                {'name': 'Tableau de Bord Responsable', 'url': 'responsables:tableau_bord'},
                {'name': 'Tournois', 'url': 'responsables:voir_tournois'},
            ]
        }
        
        return render(request, 'responsables/voir_tournois.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}", extra_tags='alert-danger')
        return redirect('responsables:tableau_bord')

@login_required
def creer_match_amical(request):
    """
    Vue pour créer un match amical entre l'équipe du responsable et une autre équipe.
    Seuls les responsables d'équipe peuvent créer des matchs amicaux.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Seuls les responsables d'équipe peuvent créer des matchs amicaux.")
        return redirect('home')
    
    # Récupérer l'équipe du responsable
    equipe_responsable = get_equipe_responsable(request.user)
    if not equipe_responsable:
        messages.error(request, "Vous devez être responsable d'une équipe pour créer des matchs amicaux.")
        return redirect('responsables:tableau_bord')
    
    if request.method == 'POST':
        equipe_adverse_id = request.POST.get('equipe_adverse')
        date = request.POST.get('date')
        lieu = request.POST.get('lieu', '')
        domicile_exterieur = request.POST.get('domicile_exterieur', 'domicile')
        notes = request.POST.get('notes', '')
        
        errors = []
        if not equipe_adverse_id:
            errors.append("Veuillez sélectionner une équipe adverse.")
        if not date:
            errors.append("Veuillez spécifier une date pour le match.")
        
        if not errors:
            try:
                from equipes.models import Equipe
                
                equipe_adverse = Equipe.objects.get(id=equipe_adverse_id)
                
                # Déterminer équipe domicile et extérieur
                if domicile_exterieur == 'domicile':
                    equipe_domicile = equipe_responsable
                    equipe_exterieur = equipe_adverse
                else:
                    equipe_domicile = equipe_adverse
                    equipe_exterieur = equipe_responsable
                
                # Créer le match amical (sans tournoi)
                match = Match(
                    equipe_a=equipe_domicile,
                    equipe_b=equipe_exterieur,
                    date=date,
                    lieu=lieu,
                    notes=notes,
                    tournoi=None,  # Match amical sans tournoi associé
                    type_match='amical'
                )
                match.save()
                
                # Envoyer une notification à l'équipe adverse
                responsable_adversaire = get_responsable_equipe(equipe_adverse)
                if responsable_adversaire:
                    # Utiliser la méthode helper pour créer la notification
                    from notifications.models import Notification
                    Notification.creer_notification_match_amical(
                        destinataire=responsable_adversaire.user,
                        equipe_a=equipe_domicile,
                        equipe_b=equipe_exterieur,
                        date_match=match.date,
                        match_id=match.id
                    )
                
                messages.success(
                    request,
                    f"Le match amical contre {equipe_adverse.nom} a été créé avec succès pour le {date}."
                )
                return redirect('matchs:detail', pk=match.id)
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        else:
            for error in errors:
                messages.error(request, error)
    
    # Récupérer toutes les équipes sauf celle du responsable
    from equipes.models import Equipe
    equipes_adverses = Equipe.objects.exclude(id=equipe_responsable.id).order_by('nom')
    
    context = {
        'equipe_responsable': equipe_responsable,
        'equipes_adverses': equipes_adverses,
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M')
    }
    
    return render(request, 'responsables/creer_match_amical.html', context)

def get_responsable_equipe(equipe):
    """
    Fonction utilitaire pour récupérer le responsable d'une équipe
    """
    from responsables.models import Responsable
    from equipes.models import MembreEquipe
    
    try:
        # Chercher un membre avec le rôle de responsable
        membre_responsable = MembreEquipe.objects.filter(
            equipe=equipe,
            utilisateur__type='responsable'
        ).first()
        
        if membre_responsable:
            responsable = Responsable.objects.filter(utilisateur=membre_responsable.utilisateur).first()
            return responsable
        
        return None
    except Exception:
        return None


     
