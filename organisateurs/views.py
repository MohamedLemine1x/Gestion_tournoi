from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.http import JsonResponse
import logging
from functools import wraps
from .models import Organisateur
from .forms import OrganisateurForm, TournoiForm, MatchForm, ResultatMatchForm
from tournois.models import Tournoi
from matchs.models import Match

logger = logging.getLogger(__name__)

def organisateur_required(view_func):
    """Décorateur qui vérifie que l'utilisateur est un organisateur."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        logger.info(f"Vérification de l'accès organisateur pour: {request.user}")
        
        # Vérifier l'authentification
        if not request.user.is_authenticated:
            logger.warning(f"Utilisateur non authentifié")
            messages.error(request, _("Vous devez vous connecter pour accéder à cette section."), extra_tags='login_required')
            return redirect('accounts:login')
            
        # Vérifier le type d'utilisateur
        if request.user.type != 'organisateur':
            logger.warning(f"L'utilisateur {request.user.username} n'est pas un organisateur")
            messages.error(request, _("Cette section est réservée aux organisateurs de tournois."), extra_tags='access_denied')
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    return wrapper

def is_organisateur(user):
    """Vérifie si l'utilisateur est un organisateur."""
    logger.debug(f"Vérification du statut organisateur pour l'utilisateur: {user.username} (id: {user.id})")
    try:
        if not user.is_authenticated:
            logger.warning(f"L'utilisateur {user} n'est pas authentifié")
            return False

        # Vérifier d'abord si l'utilisateur a le type 'organisateur'
        if user.type == 'organisateur':
            logger.debug(f"L'utilisateur {user.username} a le type 'organisateur'")
            
            # Vérifier s'il existe un modèle Organisateur associé
            try:
                # Accéder directement à la relation pour forcer le chargement
                organisateur = user.organisateur
                logger.debug(f"Instance Organisateur trouvée pour {user.username}")
                return True
            except Exception as e:
                logger.info(f"Tentative de création d'une instance Organisateur pour {user.username}")
                # Si l'accès à la relation échoue, créer l'instance immédiatement
                try:
                    from .models import Organisateur
                    organisateur, created = Organisateur.objects.get_or_create(user=user)
                    if created:
                        logger.info(f"Instance Organisateur créée pour {user.username} dans is_organisateur")
                    return True
                except Exception as inner_e:
                    logger.error(f"Échec de la création automatique d'un Organisateur pour {user.username}: {str(inner_e)}")
                    # Ne pas retourner False ici, on laisse l'utilisateur accéder quand même
                    # puisqu'il a le type 'organisateur'
                    return True
        else:
            logger.warning(f"L'utilisateur {user.username} n'est pas de type 'organisateur'")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut organisateur pour {user.username}: {str(e)}")
        return False

@login_required
def dashboard(request):
    """Vue du tableau de bord de l'organisateur."""
    logger.error(f"==== DASHBOARD ENTRY POINT ====")
    logger.error(f"User: {request.user.username} (ID: {request.user.id})")
    logger.error(f"User authenticated: {request.user.is_authenticated}")
    logger.error(f"User type: {getattr(request.user, 'type', 'TYPE_NOT_FOUND')}")
    logger.error(f"Has organisateur: {hasattr(request.user, 'organisateur')}")
    logger.error(f"Session data: {dict(request.session)}")
    logger.error(f"Request path: {request.path}")
    logger.error(f"HTTP_REFERER: {request.META.get('HTTP_REFERER', 'No referer')}")
    
    # Protection contre les boucles de redirection infinies
    if 'redirect_count' in request.session:
        request.session['redirect_count'] += 1
    else:
        request.session['redirect_count'] = 1
        
    # Si trop de redirections, arrêter la boucle et afficher une page d'erreur
    if request.session.get('redirect_count', 0) > 5:
        logger.error(f"LOOP DETECTED! Stopping after {request.session['redirect_count']} redirects")
        request.session['redirect_count'] = 0  # Réinitialiser le compteur
        error_context = {
            'title': 'Erreur de redirection',
            'message': 'Une boucle de redirection a été détectée. Veuillez contacter l\'administrateur.',
            'details': f"User: {request.user.username}, Type: {getattr(request.user, 'type', 'unknown')}",
        }
        return render(request, 'error.html', error_context)
    
    # Vérifier que l'utilisateur est bien de type organisateur
    if not request.user.is_authenticated:
        logger.error(f"Utilisateur non authentifié, redirection vers login")
        request.session['redirect_count'] = 0  # Réinitialiser le compteur
        return redirect('accounts:login')
        
    logger.error(f"User type check: {request.user.type}")
    if request.user.type != 'organisateur':
        logger.error(f"L'utilisateur {request.user.username} n'est pas un organisateur (type: {request.user.type})")
        messages.error(request, _("Cette section est réservée aux organisateurs de tournois."))
        request.session['redirect_count'] = 0  # Réinitialiser le compteur
        return redirect('home')
    
    # S'assurer que l'utilisateur a une instance Organisateur sans afficher de message d'erreur
    logger.error(f"Checking organisateur instance for {request.user.username}")
    if not hasattr(request.user, 'organisateur'):
        try:
            from .models import Organisateur
            logger.error(f"Tentative de création d'un organisateur pour {request.user.username}")
            organisateur, created = Organisateur.objects.get_or_create(user=request.user)
            logger.error(f"Created new organisateur: {created}")
            # Refresh user to ensure organisateur is loaded
            from django.contrib.auth import get_user_model
            User = get_user_model()
            request.user = User.objects.get(pk=request.user.pk)
            logger.error(f"User refreshed, has organisateur: {hasattr(request.user, 'organisateur')}")
        except Exception as create_error:
            logger.error(f"ERROR creating organisateur: {str(create_error)}")
            logger.error(f"Exception type: {type(create_error)}")
            logger.error(f"Exception details: {create_error.__dict__}")
            # Ne pas afficher de message d'erreur ici, juste logger l'erreur
            request.session['redirect_count'] = 0  # Réinitialiser le compteur
            return redirect('home')
    
    try:
        # Récupérer l'instance Organisateur directement depuis la base de données
        from .models import Organisateur
        try:
            organisateur = Organisateur.objects.get(user=request.user)
            logger.error(f"Organisateur found directly from DB: {organisateur}")
        except Organisateur.DoesNotExist:
            logger.error(f"Organisateur not found in DB, creating a new one")
            organisateur = Organisateur.objects.create(user=request.user)
            logger.error(f"New organisateur created: {organisateur}")
        
        # Récupérer les tournois et autres données
        logger.error(f"Getting tournois for organisateur: {organisateur}")
        tournois = Tournoi.objects.filter(createur=request.user)
        logger.error(f"Tournois count: {tournois.count()}")
        
        # Préparation du contexte et rendu du template
        context = {
            'tournois': tournois,
            'matchs_a_planifier': Match.objects.filter(tournoi__createur=request.user, date__isnull=True),
            'matchs_a_arbitrer': Match.objects.filter(
                tournoi__createur=request.user,
                date__isnull=False,
                score_equipe_a__isnull=True,
                score_equipe_b__isnull=True
            ),
        }
        logger.error(f"==== END DASHBOARD SUCCESS ====")
        request.session['redirect_count'] = 0  # Réinitialiser le compteur
        return render(request, 'organisateurs/dashboard.html', context)
    except Exception as e:
        logger.error(f"ERROR in dashboard view: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception details: {e.__dict__ if hasattr(e, '__dict__') else 'No dict'}")
        # Fournir un tableau de bord vide en cas d'erreur
        context = {
            'tournois': [],
            'matchs_a_planifier': [],
            'matchs_a_arbitrer': [],
            'error_message': str(e)
        }
        # Ne pas afficher de message d'erreur ici pour ne pas perturber l'utilisateur
        logger.error(f"==== END DASHBOARD ERROR ====")
        request.session['redirect_count'] = 0  # Réinitialiser le compteur
        return render(request, 'organisateurs/dashboard.html', context)

@login_required
@organisateur_required
def tournoi_create(request):
    """Vue pour la création d'un nouveau tournoi."""
    logger.info(f"Accès à la vue tournoi_create par l'utilisateur {request.user.username}")
    
    # À ce stade, l'utilisateur devrait avoir une instance Organisateur valide
    if request.method == 'POST':
        logger.info(f"Tentative de création de tournoi par {request.user.username}")
        form = TournoiForm(request.POST)
        if form.is_valid():
            try:
                # Création du tournoi
                tournoi = form.save(commit=False)
                tournoi.createur = request.user
                tournoi.save()
                
                # Enregistrement des champs personnalisés
                type_tournoi = form.cleaned_data.get('type')
                format_tournoi = form.cleaned_data.get('format')
                
                logger.info(f"Tournoi '{tournoi.nom}' créé avec succès par {request.user.username}")
                messages.success(request, _('Tournoi créé avec succès !'))
                return redirect('organisateurs:dashboard')
            except Exception as e:
                logger.error(f"Erreur lors de la création du tournoi: {str(e)}")
                messages.error(request, _("Une erreur s'est produite lors de la création du tournoi."))
        else:
            logger.warning(f"Formulaire invalide pour {request.user.username}: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        logger.info(f"Affichage du formulaire de création de tournoi pour {request.user.username}")
        form = TournoiForm()
    
    return render(request, 'organisateurs/tournoi_form.html', {'form': form})

@login_required
@organisateur_required
def tournoi_edit(request, pk):
    """Vue pour la modification d'un tournoi existant."""
    tournoi = get_object_or_404(Tournoi, pk=pk, createur=request.user)
    
    if request.method == 'POST':
        form = TournoiForm(request.POST, instance=tournoi)
        if form.is_valid():
            form.save()
            messages.success(request, _('Tournoi modifié avec succès !'))
            return redirect('organisateurs:dashboard')
    else:
        form = TournoiForm(instance=tournoi)
    
    return render(request, 'organisateurs/tournoi_form.html', {'form': form, 'tournoi': tournoi})

@login_required
@organisateur_required
def match_create(request, tournoi_pk):
    """Vue pour la création d'un nouveau match."""
    tournoi = get_object_or_404(Tournoi, pk=tournoi_pk, createur=request.user)
    
    if request.method == 'POST':
        form = MatchForm(request.POST, tournoi=tournoi)
        if form.is_valid():
            match = form.save(commit=False)
            match.tournoi = tournoi
            match.save()
            messages.success(request, _('Match créé avec succès !'))
            return redirect('organisateurs:dashboard')
    else:
        form = MatchForm(tournoi=tournoi)
    
    return render(request, 'organisateurs/match_form.html', {'form': form, 'tournoi': tournoi})

@login_required
@organisateur_required
def match_edit(request, pk):
    """Vue pour la modification d'un match existant."""
    match = get_object_or_404(Match, pk=pk, tournoi__createur=request.user)
    
    if request.method == 'POST':
        form = MatchForm(request.POST, instance=match, tournoi=match.tournoi)
        if form.is_valid():
            form.save()
            messages.success(request, _('Match modifié avec succès !'))
            return redirect('organisateurs:dashboard')
    else:
        form = MatchForm(instance=match, tournoi=match.tournoi)
    
    return render(request, 'organisateurs/match_form.html', {'form': form, 'match': match})

@login_required
@organisateur_required
def resultat_match(request, pk):
    """Vue pour la saisie des résultats d'un match."""
    match = get_object_or_404(Match, pk=pk, tournoi__createur=request.user)
    
    if request.method == 'POST':
        form = ResultatMatchForm(request.POST, instance=match)
        if form.is_valid():
            with transaction.atomic():
                match = form.save()
                match.termine = True
                match.save()
                # Mettre à jour les statistiques des équipes si nécessaire
                if hasattr(match, 'update_equipe_stats'):
                    match.update_equipe_stats()
            messages.success(request, _('Résultat enregistré avec succès !'))
            return redirect('organisateurs:dashboard')
    else:
        form = ResultatMatchForm(instance=match)
    
    return render(request, 'organisateurs/resultat_match.html', {'form': form, 'match': match})

@login_required
@organisateur_required
def get_equipes_tournoi(request, tournoi_pk):
    """Vue API pour récupérer les équipes d'un tournoi."""
    tournoi = get_object_or_404(Tournoi, pk=tournoi_pk, createur=request.user)
    equipes = tournoi.equipes.all()
    data = [{'id': equipe.id, 'nom': equipe.nom} for equipe in equipes]
    return JsonResponse(data, safe=False)
