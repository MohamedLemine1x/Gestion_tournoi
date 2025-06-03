# tournois/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import Tournoi, MatchTournoi, InscriptionTournoi
from equipes.models import Equipe
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from matchs.models import Match
from django.db.models import Q
from equipes.models import MembreEquipe

@login_required
def modifier_tournoi(request, pk):
    """
    Vue pour modifier un tournoi existant.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier que l'utilisateur est le créateur du tournoi
    if tournoi.createur != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier ce tournoi.")
        return redirect('tournois:detail', pk=tournoi.id)
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        nom = request.POST.get('nom')
        description = request.POST.get('description', '')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin', None)
        lieu = request.POST.get('lieu', '')
        nombre_equipes_max = request.POST.get('nombre_equipes_max', tournoi.nombre_equipes_max)
        
        # Validation basique
        errors = []
        if not nom:
            errors.append("Le nom du tournoi est obligatoire.")
        if not date_debut:
            errors.append("La date de début est obligatoire.")
            
        # Si pas d'erreurs, modifier le tournoi
        if not errors:
            try:
                tournoi.nom = nom
                tournoi.description = description
                tournoi.date_debut = date_debut
                tournoi.date_fin = date_fin if date_fin else None
                tournoi.lieu = lieu
                tournoi.nombre_equipes_max = nombre_equipes_max
                
                # Gérer l'upload du logo s'il existe
                logo_file = request.FILES.get('logo')
                if logo_file:
                    # Vérifier le type de fichier (seulement image)
                    if not logo_file.content_type.startswith('image/'):
                        errors.append("Le fichier logo doit être une image (JPG, PNG, GIF).")
                    # Vérifier la taille du fichier (max 2MB)
                    elif logo_file.size > 2 * 1024 * 1024:
                        errors.append("La taille du logo ne doit pas dépasser 2MB.")
                    else:
                        # Si un ancien logo existe, le supprimer
                        if tournoi.logo:
                            import os
                            if os.path.isfile(tournoi.logo.path):
                                os.remove(tournoi.logo.path)
                        tournoi.logo = logo_file
                
                if not errors:
                    tournoi.save()
                    messages.success(request, f"Le tournoi '{tournoi.nom}' a été modifié avec succès.")
                    return redirect('tournois:detail', pk=tournoi.id)
                else:
                    # Afficher les erreurs liées au logo
                    for error in errors:
                        messages.error(request, error)
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        else:
            # Afficher les erreurs
            for error in errors:
                messages.error(request, error)
    
    # Préparer les données pour le template
    context = {
        'tournoi': tournoi,
        'today': timezone.now().date(),
        'title': f'Modifier le tournoi {tournoi.nom}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'tournois/tournoi_form.html', context)

@login_required
def supprimer_tournoi(request, pk):
    """
    Vue pour supprimer un tournoi.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier que l'utilisateur est le créateur du tournoi
    if tournoi.createur != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce tournoi.")
        return redirect('tournois:detail', pk=tournoi.id)
    
    if request.method == 'POST':
        nom = tournoi.nom
        tournoi.delete()
        messages.success(request, f"Le tournoi '{nom}' a été supprimé avec succès.")
        return redirect('tournois:liste')
    
    # Confirmation de suppression
    return render(request, 'tournois/supprimer_tournoi.html', {'tournoi': tournoi})


@login_required
def inscrire_equipe(request, pk):
    """
    Vue pour inscrire une équipe à un tournoi.
    """
    # Vérifier que l'utilisateur est un responsable d'équipe
    if request.user.type != 'responsable':
        messages.error(request, "Seuls les responsables d'équipe peuvent inscrire une équipe à un tournoi.")
        return redirect('tournois:detail', pk=pk)
    
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Si le tournoi est terminé, empêcher l'inscription
    if tournoi.est_termine():
        messages.error(request, "Ce tournoi est terminé. Impossible d'inscrire de nouvelles équipes.")
        return redirect('tournois:detail', pk=pk)
    
    # Récupérer l'équipe dont l'utilisateur est responsable
    try:
        equipe = Equipe.objects.get(responsable__user=request.user)
        
        # Vérifier si l'équipe est déjà inscrite
        if InscriptionTournoi.objects.filter(tournoi=tournoi, equipe=equipe).exists():
            messages.warning(request, "Votre équipe est déjà inscrite à ce tournoi.")
            return redirect('tournois:detail', pk=pk)
        
        # Traitement de l'inscription
        if request.method == 'POST':
            try:
                inscription = InscriptionTournoi(
                    tournoi=tournoi,
                    equipe=equipe
                )
                inscription.save()
                
                messages.success(request, f"Votre équipe '{equipe.nom}' a été inscrite au tournoi '{tournoi.nom}'.")
                return redirect('tournois:detail', pk=pk)
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        
        # Procéder directement à l'inscription sans afficher de template
        try:
            inscription = InscriptionTournoi(
                tournoi=tournoi,
                equipe=equipe
            )
            inscription.save()
            
            messages.success(request, f"Votre équipe '{equipe.nom}' a été inscrite au tournoi '{tournoi.nom}'.")
            return redirect('tournois:detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'inscription: {str(e)}")
            return redirect('tournois:detail', pk=pk)
        
    except Equipe.DoesNotExist:
        messages.error(request, "Vous devez d'abord créer une équipe pour pouvoir l'inscrire à un tournoi.")
        return redirect('equipes:gestion_equipe')

def resultats(request, pk):
    """
    Vue pour afficher tous les résultats des matchs d'un tournoi.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Récupérer tous les matchs terminés
    matchs_termines = MatchTournoi.objects.filter(
        tournoi=tournoi,
        termine=True
    ).order_by('-date_match')
    
    # Récupérer tous les matchs à venir
    matchs_a_venir = MatchTournoi.objects.filter(
        tournoi=tournoi,
        termine=False
    ).order_by('date_match')
    
    return render(request, 'tournois/resultats.html', {
        'tournoi': tournoi,
        'matchs_termines': matchs_termines,
        'matchs_a_venir': matchs_a_venir
    })

def classement(request, pk):
    """
    Vue pour afficher le classement des équipes dans un tournoi.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Récupérer toutes les équipes inscrites
    inscriptions = InscriptionTournoi.objects.filter(tournoi=tournoi)
    equipes = [inscription.equipe for inscription in inscriptions]
    
    # Calculer les statistiques pour chaque équipe
    classement_equipes = []
    
    for equipe in equipes:
        # Matchs à domicile
        matchs_domicile = MatchTournoi.objects.filter(
            tournoi=tournoi,
            equipe_domicile=equipe,
            termine=True
        )
        
        # Matchs à l'extérieur
        matchs_exterieur = MatchTournoi.objects.filter(
            tournoi=tournoi,
            equipe_exterieur=equipe,
            termine=True
        )
        
        # Initialiser les statistiques
        victoires = 0
        nuls = 0
        defaites = 0
        buts_pour = 0
        buts_contre = 0
        
        # Calculer les statistiques pour les matchs à domicile
        for match in matchs_domicile:
            buts_pour += match.score_domicile
            buts_contre += match.score_exterieur
            
            if match.score_domicile > match.score_exterieur:
                victoires += 1
            elif match.score_domicile == match.score_exterieur:
                nuls += 1
            else:
                defaites += 1
        
        # Calculer les statistiques pour les matchs à l'extérieur
        for match in matchs_exterieur:
            buts_pour += match.score_exterieur
            buts_contre += match.score_domicile
            
            if match.score_exterieur > match.score_domicile:
                victoires += 1
            elif match.score_exterieur == match.score_domicile:
                nuls += 1
            else:
                defaites += 1
        
        # Calculer les points (3 points pour une victoire, 1 pour un nul)
        points = (victoires * 3) + nuls
        
        # Calculer la différence de buts
        difference_buts = buts_pour - buts_contre
        
        # Ajouter l'équipe au classement
        classement_equipes.append({
            'equipe': equipe,
            'points': points,
            'matchs_joues': victoires + nuls + defaites,
            'victoires': victoires,
            'nuls': nuls,
            'defaites': defaites,
            'buts_pour': buts_pour,
            'buts_contre': buts_contre,
            'difference_buts': difference_buts
        })
    
    # Trier le classement par points, puis par différence de buts
    classement_equipes.sort(key=lambda x: (x['points'], x['difference_buts']), reverse=True)
    
    return render(request, 'tournois/classement.html', {
        'tournoi': tournoi,
        'classement': classement_equipes
    })

def statistiques(request, pk):
    """
    Vue pour afficher des statistiques détaillées sur un tournoi.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Récupérer tous les matchs terminés
    matchs_termines = MatchTournoi.objects.filter(
        tournoi=tournoi,
        termine=True
    )
    
    # Nombre total de buts
    total_buts = 0
    for match in matchs_termines:
        total_buts += match.score_domicile + match.score_exterieur
    
    # Moyenne de buts par match
    moyenne_buts = total_buts / matchs_termines.count() if matchs_termines.count() > 0 else 0
    
    # Equipe ayant marqué le plus de buts
    equipes_stats = {}
    for match in matchs_termines:
        # Buts de l'équipe à domicile
        if match.equipe_domicile.id not in equipes_stats:
            equipes_stats[match.equipe_domicile.id] = {
                'equipe': match.equipe_domicile,
                'buts_marques': 0,
                'buts_encaisses': 0
            }
        equipes_stats[match.equipe_domicile.id]['buts_marques'] += match.score_domicile
        equipes_stats[match.equipe_domicile.id]['buts_encaisses'] += match.score_exterieur
        
        # Buts de l'équipe à l'extérieur
        if match.equipe_exterieur.id not in equipes_stats:
            equipes_stats[match.equipe_exterieur.id] = {
                'equipe': match.equipe_exterieur,
                'buts_marques': 0,
                'buts_encaisses': 0
            }
        equipes_stats[match.equipe_exterieur.id]['buts_marques'] += match.score_exterieur
        equipes_stats[match.equipe_exterieur.id]['buts_encaisses'] += match.score_domicile
    
    # Convertir equipes_stats en liste pour pouvoir trier
    equipes_liste = list(equipes_stats.values())
    
    # Meilleure attaque (équipe ayant marqué le plus de buts)
    equipes_liste.sort(key=lambda x: x['buts_marques'], reverse=True)
    meilleure_attaque = equipes_liste[0] if equipes_liste else None
    
    # Meilleure défense (équipe ayant encaissé le moins de buts)
    equipes_liste.sort(key=lambda x: x['buts_encaisses'])
    meilleure_defense = equipes_liste[0] if equipes_liste else None
    
    return render(request, 'tournois/statistiques.html', {
        'tournoi': tournoi,
        'nb_matchs_joues': matchs_termines.count(),
        'total_buts': total_buts,
        'moyenne_buts': moyenne_buts,
        'meilleure_attaque': meilleure_attaque,
        'meilleure_defense': meilleure_defense,
        'equipes_stats': equipes_liste
    })

@login_required
def tableau_bord(request):
    """
    Vue pour afficher le tableau de bord des tournois adapté au type d'utilisateur.
    - Pour les organisateurs : affiche les tournois créés
    - Pour les responsables : affiche les tournois auxquels l'équipe est inscrite
    """
    user_type = request.user.type
    
    # Vérifier si l'utilisateur est organisateur ou responsable
    if user_type not in ['organisateur', 'responsable']:
        messages.error(request, "Cette fonctionnalité est réservée aux organisateurs et responsables d'équipe.")
        return redirect('home')
    
    # Variables par défaut
    tournois_crees = []
    tournois_inscrits = []
    prochains_matchs = []
    
    # Fonctionnalités pour organisateur
    if user_type == 'organisateur':
        # Récupérer les tournois créés par l'utilisateur
        tournois_crees = Tournoi.objects.filter(createur=request.user).order_by('-date_creation')
        
        # Récupérer les statistiques
        nb_tournois_crees = tournois_crees.count()
        nb_tournois_inscrits = 0
        
        context = {
            'titre': "Tableau de bord de l'organisateur",
            'tournois_crees': tournois_crees,
            'nb_tournois_crees': nb_tournois_crees,
            'nb_tournois_inscrits': nb_tournois_inscrits,
            'est_organisateur': True,
            'est_responsable': False
        }
    
    # Fonctionnalités pour responsable d'équipe
    elif user_type == 'responsable':
        # Récupérer l'équipe de l'utilisateur
        try:
            equipe = Equipe.objects.get(responsable__user=request.user)
            
            # Récupérer les tournois auxquels l'équipe est inscrite
            inscriptions = InscriptionTournoi.objects.filter(equipe=equipe)
            tournois_inscrits = [inscription.tournoi for inscription in inscriptions]
            
            # Récupérer les matchs à venir
            for tournoi in tournois_inscrits:
                matchs = MatchTournoi.objects.filter(
                    tournoi=tournoi,
                    date_match__gt=timezone.now(),
                    termine=False
                ).filter(Q(equipe_domicile=equipe) | Q(equipe_exterieur=equipe)).order_by('date_match')[:5]
                prochains_matchs.extend(list(matchs))
            
            # Trier les prochains matchs par date
            prochains_matchs.sort(key=lambda x: x.date_match)
            
            # Récupérer les statistiques
            nb_tournois_crees = 0
            nb_tournois_inscrits = len(tournois_inscrits)
            
            context = {
                'titre': "Tableau de bord du responsable d'équipe",
                'equipe': equipe,
                'tournois_inscrits': tournois_inscrits,
                'prochains_matchs': prochains_matchs[:5],  # Limiter à 5 matchs maximum
                'nb_tournois_crees': nb_tournois_crees,
                'nb_tournois_inscrits': nb_tournois_inscrits,
                'est_organisateur': False,
                'est_responsable': True
            }
        except Equipe.DoesNotExist:
            messages.warning(request, "Vous n'avez pas encore créé d'équipe.")
            context = {
                'titre': "Tableau de bord du responsable d'équipe",
                'est_organisateur': False,
                'est_responsable': True,
                'nb_tournois_crees': 0,
                'nb_tournois_inscrits': 0
            }
    
    return render(request, 'tournois/tableau_bord.html', context)



def liste_tournois(request):
    """
    Vue pour afficher la liste de tous les tournois.
    """
    tournois = Tournoi.objects.all().order_by('-date_debut')
    today = timezone.now().date()
    
    # Pour chaque tournoi, déterminer s'il est terminé ou non
    for tournoi in tournois:
        tournoi.est_termine = tournoi.date_fin and tournoi.date_fin < today
    
    return render(request, 'tournois/liste_tournois.html', {
        'tournois': tournois,
        'today': today
    })


@login_required
def detail_tournoi(request, pk):
    """
    Vue pour afficher les détails d'un tournoi.
    """
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Récupérer la liste des équipes inscrites
    equipes_inscrites = InscriptionTournoi.objects.filter(tournoi=tournoi).select_related('equipe')
    nb_equipes = equipes_inscrites.count()
    
    # Récupérer la liste des matchs du tournoi
    matchs_a_venir = MatchTournoi.objects.filter(
        tournoi=tournoi,
        termine=False
    ).order_by('date_match')
    
    matchs_termines = MatchTournoi.objects.filter(
        tournoi=tournoi,
        termine=True
    ).order_by('-date_match')
    
    # Calculer les statistiques
    nb_matchs_a_venir = matchs_a_venir.count()
    nb_matchs_termines = matchs_termines.count()
    nb_matchs = nb_matchs_a_venir + nb_matchs_termines
    
    # Calculer le total des buts marqués
    total_buts = 0
    for match in matchs_termines:
        if match.score_domicile is not None and match.score_exterieur is not None:
            total_buts += match.score_domicile + match.score_exterieur
    
    # Calculer la moyenne de buts par match
    moyenne_buts = total_buts / nb_matchs_termines if nb_matchs_termines > 0 else 0
    
    # Vérifier si l'utilisateur est un responsable d'équipe et possède une équipe
    est_responsable = request.user.type == 'responsable'
    equipe_utilisateur = None
    deja_inscrit = False
    
    if est_responsable:
        try:
            equipe_utilisateur = Equipe.objects.get(responsable__user=request.user)
            deja_inscrit = InscriptionTournoi.objects.filter(tournoi=tournoi, equipe=equipe_utilisateur).exists()
        except Equipe.DoesNotExist:
            equipe_utilisateur = None
    
    # Vérifier si l'utilisateur est l'organisateur du tournoi
    est_organisateur = request.user == tournoi.createur
    
    # Préparer le contexte pour le template
    from django.utils import timezone
    today = timezone.now().date()
    
    context = {
        'tournoi': tournoi,
        'equipes_inscrites': equipes_inscrites,
        'matchs_a_venir': matchs_a_venir[:5],  # Limiter à 5 matchs pour l'affichage
        'matchs_termines': matchs_termines[:5],  # Limiter à 5 matchs pour l'affichage
        'est_responsable': est_responsable,
        'equipe_utilisateur': equipe_utilisateur,
        'deja_inscrit': deja_inscrit,
        'est_organisateur': est_organisateur,
        'est_createur': est_organisateur,  # Alias pour compatibilité template
        'organisateur': tournoi.createur,
        'today': today,  # Date actuelle pour la comparaison dans le template
        
        # Statistiques
        'nb_equipes': nb_equipes,
        'nb_matchs': nb_matchs,
        'nb_matchs_a_venir': nb_matchs_a_venir,
        'nb_matchs_termines': nb_matchs_termines,
        'total_buts': total_buts,
        'moyenne_buts': round(moyenne_buts, 1),
        'pourcentage_complet': int((nb_equipes / tournoi.nombre_equipes_max) * 100) if tournoi.nombre_equipes_max > 0 else 0,
        'places_restantes': max(0, tournoi.nombre_equipes_max - nb_equipes),
    }
    
    return render(request, 'tournois/detail_tournoi.html', context)

def planifier_matchs(request, pk):
    """
    Vue permettant de planifier des matchs pour un tournoi spécifique.
    """
    # Récupérer le tournoi et vérifier qu'il existe
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier si l'utilisateur est le créateur du tournoi ou un administrateur
    if request.user != tournoi.createur and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à planifier des matchs pour ce tournoi.")
        return redirect('tournois:detail', pk=tournoi.id)
    
    # Récupérer les matchs existants pour ce tournoi
    matchs = MatchTournoi.objects.filter(tournoi=tournoi).order_by('date_match')
    
    # Compter les matchs terminés et à venir pour les statistiques
    matchs_termines = matchs.filter(termine=True).count()
    matchs_a_venir = matchs.filter(termine=False).count()
    
    # Récupérer les équipes inscrites au tournoi
    inscriptions = InscriptionTournoi.objects.filter(tournoi=tournoi)
    equipes = [inscription.equipe for inscription in inscriptions]
    
    # Traitement du formulaire si soumis
    if request.method == 'POST':
        # Récupérer les données du formulaire
        equipe_a_id = request.POST.get('equipe_domicile')
        equipe_b_id = request.POST.get('equipe_exterieur')
        date_str = request.POST.get('date')
        lieu = request.POST.get('lieu', '')
        
        # Validation de base
        errors = []
        
        # Vérifier que les équipes sont sélectionnées et différentes
        if not equipe_a_id:
            errors.append("Veuillez sélectionner l'équipe domicile.")
        if not equipe_b_id:
            errors.append("Veuillez sélectionner l'équipe extérieure.")
        if equipe_a_id and equipe_b_id and equipe_a_id == equipe_b_id:
            errors.append("Les deux équipes ne peuvent pas être identiques.")
        
        # Vérifier la date
        if not date_str:
            errors.append("Veuillez spécifier une date et heure pour le match.")
        
        # Si pas d'erreurs, créer le match
        if not errors:
            try:
                # Récupérer les objets Equipe
                equipe_a = Equipe.objects.get(id=equipe_a_id)
                equipe_b = Equipe.objects.get(id=equipe_b_id)
                
                # Vérifier que les équipes sont inscrites au tournoi
                if InscriptionTournoi.objects.filter(tournoi=tournoi, equipe=equipe_a).exists() and \
                   InscriptionTournoi.objects.filter(tournoi=tournoi, equipe=equipe_b).exists():
                    
                    # Créer et sauvegarder le match
                    match = MatchTournoi(
                        tournoi=tournoi,
                        equipe_domicile=equipe_a,
                        equipe_exterieur=equipe_b,
                        date_match=date_str,
                        lieu_match=lieu,
                        termine=False
                    )
                    match.save()
                    
                    # Message de succès et redirection
                    messages.success(request, f"Le match {equipe_a.nom} vs {equipe_b.nom} a été planifié avec succès.")
                    return redirect('tournois:planifier_matchs', pk=tournoi.id)
                else:
                    messages.error(request, "Une des équipes n'est pas inscrite au tournoi.")
            
            except Exception as e:
                # En cas d'erreur, ajouter un message d'erreur
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        else:
            # S'il y a des erreurs de validation, les afficher
            for error in errors:
                messages.error(request, error)
    
    # Contexte pour le template
    context = {
        'tournoi': tournoi,
        'matchs': matchs,
        'matchs_termines': matchs_termines,
        'matchs_a_venir': matchs_a_venir,
        'equipes': equipes,
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M')  # Format pour input datetime-local
    }
    
    # Rendu du template
    return render(request, 'tournois/planifier_matchs.html', context)

def detail_match(request, match_id):
    """
    Vue permettant d'afficher les détails d'un match.
    """
    match = get_object_or_404(MatchTournoi, id=match_id)
    tournoi = match.tournoi
    
    # Vérifier si le match est terminé
    match_termine = match.termine
    
    # Déterminer si l'utilisateur est autorisé à modifier le résultat
    peut_modifier = request.user == tournoi.createur or request.user.is_staff
    
    context = {
        'match': match,
        'tournoi': tournoi,
        'match_termine': match_termine,
        'peut_modifier': peut_modifier
    }
    
    return render(request, 'tournois/detail_match.html', context)

def enregistrer_resultat(request, match_id):
    """
    Vue permettant d'enregistrer le résultat d'un match.
    """
    match = get_object_or_404(MatchTournoi, id=match_id)
    tournoi = match.tournoi
    
    # Vérifier que l'utilisateur est autorisé (créateur du tournoi ou admin)
    if request.user != tournoi.createur and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à enregistrer des résultats pour ce tournoi.")
        return redirect('tournois:detail_match', match_id=match.id)
    
    # Vérifier que le match n'est pas déjà terminé
    if match.termine:
        messages.error(request, "Ce match est déjà terminé. Impossible de modifier le résultat.")
        return redirect('tournois:detail_match', match_id=match.id)
    
    if request.method == 'POST':
        # Récupérer les scores
        score_domicile = request.POST.get('score_domicile')
        score_exterieur = request.POST.get('score_exterieur')
        
        # Validation de base
        errors = []
        
        try:
            # Convertir en entiers
            score_domicile = int(score_domicile)
            score_exterieur = int(score_exterieur)
            
            # Vérifier que les scores sont positifs
            if score_domicile < 0 or score_exterieur < 0:
                errors.append("Les scores doivent être des nombres positifs.")
        except (ValueError, TypeError):
            errors.append("Les scores doivent être des nombres entiers.")
        
        if not errors:
            # Enregistrer le résultat
            match.score_domicile = score_domicile
            match.score_exterieur = score_exterieur
            match.termine = True
            match.save()
            
            # Message de succès
            if score_domicile > score_exterieur:
                vainqueur = match.equipe_domicile
            elif score_exterieur > score_domicile:
                vainqueur = match.equipe_exterieur
            else:
                vainqueur = None
                
            if vainqueur:
                messages.success(request, f"Résultat enregistré : {match.equipe_domicile.nom} {score_domicile} - {score_exterieur} {match.equipe_exterieur.nom}. Vainqueur : {vainqueur.nom}")
            else:
                messages.success(request, f"Résultat enregistré : {match.equipe_domicile.nom} {score_domicile} - {score_exterieur} {match.equipe_exterieur.nom}. Match nul.")
            
            return redirect('tournois:detail_match', match_id=match.id)
        else:
            # Afficher les erreurs
            for error in errors:
                messages.error(request, error)
    
    # Afficher le formulaire d'enregistrement de résultat
    context = {
        'match': match,
        'tournoi': tournoi
    }
    return render(request, 'tournois/enregistrer_resultat.html', context)

@login_required
def supprimer_match(request, match_id):
    """
    Vue permettant de supprimer un match.
    """
    match = get_object_or_404(MatchTournoi, id=match_id)
    tournoi = match.tournoi
    
    # Vérifier que l'utilisateur est autorisé (créateur du tournoi ou admin)
    if request.user != tournoi.createur and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer des matchs pour ce tournoi.")
        return redirect('tournois:detail_match', match_id=match.id)
    
    # Vérifier que le match n'est pas déjà terminé
    if match.termine:
        messages.error(request, "Ce match est déjà terminé. Impossible de le supprimer.")
        return redirect('tournois:detail_match', match_id=match.id)
    
    if request.method == 'POST':
        # Récupérer l'ID du tournoi avant de supprimer le match
        tournoi_id = match.tournoi.id
        
        # Stocker les noms des équipes pour le message
        equipe_a_nom = match.equipe_domicile.nom
        equipe_b_nom = match.equipe_exterieur.nom
        
        # Supprimer le match
        match.delete()
        
        # Message de succès
        messages.success(request, f"Le match entre {equipe_a_nom} et {equipe_b_nom} a été supprimé avec succès.")
        
        # Rediriger vers la page de planification des matchs du tournoi
        return redirect('tournois:planifier_matchs', pk=tournoi_id)
    
    # Afficher la page de confirmation de suppression
    context = {
        'match': match,
        'tournoi': tournoi
    }
    return render(request, 'tournois/supprimer_match.html', context)

@login_required
def redirect_to_organisateur_create(request):
    """
    Vue pour créer un nouveau tournoi - réservée aux organisateurs
    """
    # Vérifier si l'utilisateur est un organisateur
    if request.user.type != 'organisateur':
        messages.error(request, "Vous devez être un organisateur pour créer un tournoi.")
        return redirect('tournois:liste')
    
    # Traitement du formulaire si méthode POST
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            nom = request.POST.get('nom')
            description = request.POST.get('description', '')
            date_debut = request.POST.get('date_debut')
            date_fin = request.POST.get('date_fin', None)
            lieu = request.POST.get('lieu', '')
            nombre_equipes_max = int(request.POST.get('nombre_equipes_max', 16))
            
            # Validation basique
            errors = []
            if not nom:
                errors.append("Le nom du tournoi est obligatoire.")
            if not date_debut:
                errors.append("La date de début est obligatoire.")
            
            # Si pas d'erreurs, créer le tournoi
            if not errors:
                tournoi = Tournoi(
                    nom=nom,
                    description=description,
                    date_debut=date_debut,
                    date_fin=date_fin if date_fin else None,
                    lieu=lieu,
                    nombre_equipes_max=nombre_equipes_max,
                    createur=request.user
                )
                
                # Gérer l'upload du logo s'il existe
                logo_file = request.FILES.get('logo')
                if logo_file:
                    # Vérifier le type de fichier (seulement image)
                    if not logo_file.content_type.startswith('image/'):
                        errors.append("Le fichier logo doit être une image (JPG, PNG, GIF).")
                    # Vérifier la taille du fichier (max 2MB)
                    elif logo_file.size > 2 * 1024 * 1024:
                        errors.append("La taille du logo ne doit pas dépasser 2MB.")
                    else:
                        tournoi.logo = logo_file
                
                if not errors:
                    tournoi.save()
                    messages.success(request, f"Le tournoi '{tournoi.nom}' a été créé avec succès.")
                    return redirect('tournois:detail', pk=tournoi.id)
                else:
                    # Afficher les erreurs liées au logo
                    for error in errors:
                        messages.error(request, error)
            else:
                # Afficher les erreurs
                for error in errors:
                    messages.error(request, error)
        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
    
    # Afficher le formulaire pour la création de tournoi
    return render(request, 'tournois/tournoi_form.html', {
        'title': 'Créer un nouveau tournoi',
        'submit_text': 'Créer le tournoi',
        'today': timezone.now().date()
    })

@login_required
def redirect_to_organisateur_edit(request, pk):
    """
    Vue pour modifier un tournoi - réservée aux organisateurs
    """
    # Récupérer le tournoi
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier si l'utilisateur est un organisateur et est le créateur du tournoi
    if request.user.type != 'organisateur':
        messages.error(request, "Vous devez être un organisateur pour modifier un tournoi.")
        return redirect('tournois:detail', pk=pk)
    
    if request.user != tournoi.createur:
        messages.error(request, "Vous ne pouvez modifier que les tournois que vous avez créés.")
        return redirect('tournois:detail', pk=pk)
    
    # Au lieu de rediriger, utiliser directement la fonction modifier_tournoi
    return modifier_tournoi(request, pk)

@login_required
def redirect_to_organisateur_match_create(request, pk):
    """
    Vue pour créer un match dans un tournoi - réservée aux organisateurs
    """
    # Récupérer le tournoi
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier si l'utilisateur est un organisateur et est le créateur du tournoi
    if request.user.type != 'organisateur':
        messages.error(request, "Vous devez être un organisateur pour créer un match.")
        return redirect('tournois:detail', pk=pk)
    
    if request.user != tournoi.createur:
        messages.error(request, "Vous ne pouvez ajouter des matchs qu'aux tournois que vous avez créés.")
        return redirect('tournois:detail', pk=pk)
    
    # Rediriger vers la vue de planification des matchs
    return redirect('tournois:planifier_matchs', pk=pk)

@login_required
def details_participants(request, pk):
    """
    Vue permettant aux organisateurs de voir les détails des équipes et des participants
    inscrits à leur tournoi.
    """
    # Vérifier si l'utilisateur est un organisateur
    if request.user.type != 'organisateur':
        messages.error(request, "Cette page est réservée aux organisateurs.")
        return redirect('tournois:detail', pk=pk)
    
    # Récupérer le tournoi
    tournoi = get_object_or_404(Tournoi, id=pk)
    
    # Vérifier si l'utilisateur est le créateur du tournoi
    if tournoi.createur != request.user:
        messages.error(request, "Vous ne pouvez voir les détails que des tournois que vous avez créés.")
        return redirect('organisateurs:dashboard')
    
    # Récupérer les inscriptions avec les équipes
    inscriptions = InscriptionTournoi.objects.filter(tournoi=tournoi).select_related('equipe')
    
    # Récupérer les membres de chaque équipe
    equipes_details = []
    for inscription in inscriptions:
        equipe = inscription.equipe
        membres = MembreEquipe.objects.filter(equipe=equipe).select_related('utilisateur')
        equipes_details.append({
            'equipe': equipe,
            'date_inscription': inscription.date_inscription,
            'membres': membres,
            'responsable': equipe.responsable,
            'nombre_membres': membres.count()
        })
    
    context = {
        'tournoi': tournoi,
        'equipes_details': equipes_details,
        'nombre_equipes': len(equipes_details)
    }
    
    return render(request, 'tournois/details_participants.html', context)