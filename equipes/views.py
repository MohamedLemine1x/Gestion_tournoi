from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied
from .models import Equipe, MembreEquipe
from .forms import EquipeForm, MembreEquipeForm, AjoutMembreEmailForm
from responsables.models import Responsable
import logging
from accounts.models import CustomUser
from django.db import transaction
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from functools import wraps
from utils.redirects import redirect_by_user_type

# Configuration du logger
logger = logging.getLogger(__name__)

def get_equipe_responsable(user):
    """Fonction utilitaire pour récupérer l'équipe d'un responsable"""
    try:
        # Vérifier d'abord que l'utilisateur est un responsable
        if user.type != 'responsable':
            return None
            
        # Récupérer le profil responsable
        try:
            responsable = Responsable.objects.get(user=user)
        except Responsable.DoesNotExist:
            # Créer le profil responsable s'il n'existe pas encore
            responsable = Responsable.objects.create(user=user)
            
        # Récupérer l'équipe associée au responsable
        try:
            equipe = Equipe.objects.get(responsable=responsable)
            return equipe
        except Equipe.DoesNotExist:
            return None
            
    except Exception as e:
        logger.error(f"Error checking for responsable team: {str(e)}")
        return None

@login_required
def gestion_equipe(request):
    """
    Vue principale pour la gestion d'une équipe par un responsable.
    Permet de créer une équipe ou de gérer les membres d'une équipe existante.
    """
    if request.user.type != 'responsable':
        messages.error(request, "Accès réservé aux responsables d'équipe.", extra_tags='alert-danger')
        return redirect('home')
    
    # Récupérer l'équipe du responsable s'il en a une
    equipe = get_equipe_responsable(request.user)
    
    # Si l'utilisateur n'a pas d'équipe et souhaite en créer une
    if request.method == 'POST' and 'create_team' in request.POST and not equipe:
        form = EquipeForm(request.POST, request.FILES)
        if form.is_valid():
            # Créer ou récupérer le profil responsable
            responsable, created = Responsable.objects.get_or_create(user=request.user)
            
            equipe = form.save(commit=False)
            equipe.responsable = responsable
            equipe.save()
            
            logger.info(f"Équipe créée: {equipe.nom} par {request.user.username}")
            messages.success(request, "Votre équipe a été créée avec succès", extra_tags='alert-success')
            return redirect('equipes:gestion_equipe')
    elif not equipe:
        form = EquipeForm()
    
    # Gestion des membres de l'équipe - AJOUT PAR EMAIL PRINCIPAL
    form_membre_email = None
    if equipe:
        if request.method == 'POST' and 'add_member_email' in request.POST:
            form_membre_email = AjoutMembreEmailForm(request.POST)
            if form_membre_email.is_valid():
                try:
                    email = form_membre_email.cleaned_data['email']
                    position = form_membre_email.cleaned_data['position']
                    
                    # Vérifier si l'équipe a atteint sa limite de membres
                    if equipe.est_complete():
                        messages.error(
                            request,
                            "L'équipe a atteint sa limite de 20 membres.",
                            extra_tags='alert-danger'
                        )
                        return redirect('equipes:gestion_equipe')
                    
                    # Vérifier si l'utilisateur existe déjà
                    user = CustomUser.objects.filter(email=email).first()
                    
                    if user:
                        # Vérifier si l'utilisateur est déjà membre de l'équipe
                        if MembreEquipe.objects.filter(equipe=equipe, utilisateur=user).exists():
                            messages.warning(request, f"{user.username} est déjà membre de votre équipe", extra_tags='alert-warning')
                            return redirect('equipes:detail_equipe', equipe_id=equipe.id)
                        
                        # Ajouter l'utilisateur existant à l'équipe
                        membre = MembreEquipe.objects.create(
                            equipe=equipe,
                            utilisateur=user,
                            position=position,
                            is_new=True
                        )
                        
                        messages.success(request, f"{user.username} a été ajouté à votre équipe avec succès", extra_tags='alert-success')
                        return redirect('equipes:detail_equipe', equipe_id=equipe.id)
                    else:
                        # Créer un nouvel utilisateur
                        temp_password = get_random_string(12)
                        username = email.split('@')[0]
                        base_username = username
                        counter = 1
                        
                        # S'assurer que le username est unique
                        while CustomUser.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1
                        
                        # Créer l'utilisateur
                        new_user = CustomUser.objects.create_user(
                            username=username,
                            email=email,
                            password=temp_password,
                            type='participant',
                            is_active=True
                        )
                        
                        # Créer le membre
                        membre = MembreEquipe.objects.create(
                            equipe=equipe,
                            utilisateur=new_user,
                            position=position,
                            is_new=True
                        )
                        
                        # Envoyer un email avec les identifiants (code simplifié)
                        email_success, email_message = envoyer_invitation_email(request, equipe, new_user, temp_password)
                        
                        if email_success:
                            messages.success(
                                request, 
                                f"Un compte a été créé pour {email} et un email d'invitation a été envoyé", 
                                extra_tags='alert-success'
                            )
                        else:
                            messages.warning(
                                request, 
                                f"Le membre a été ajouté mais l'email n'a pas pu être envoyé. Raison : {email_message}", 
                                extra_tags='alert-warning'
                            )
                        
                        return redirect('equipes:detail_equipe', equipe_id=equipe.id)
                except Exception as e:
                    messages.error(
                        request,
                        f"Une erreur est survenue lors de la création de l'invitation : {str(e)}",
                        extra_tags='alert-danger'
                    )
                return redirect('equipes:gestion_equipe')
            else:
                # Afficher les erreurs de validation du formulaire
                for field, errors in form_membre_email.errors.items():
                    for error in errors:
                        messages.error(request, error, extra_tags='alert-danger')
        else:
            form_membre_email = AjoutMembreEmailForm()
    
    # Récupérer les membres de l'équipe
    membres = []
    if equipe:
        membres = MembreEquipe.objects.filter(equipe=equipe)
    
    context = {
        'equipe': equipe,
        'form': form if not equipe else None,
        'form_membre_email': form_membre_email if equipe else None,
        'membres': membres
    }
    
    return render(request, 'equipes/gestion_equipe.html', context)

@login_required
def modifier_equipe(request, equipe_id):
    equipe = get_object_or_404(Equipe, id=equipe_id)
    
    # Vérifier que l'utilisateur est le responsable de cette équipe
    if not equipe.responsable or equipe.responsable.user != request.user:
        return redirect('equipes:gestion_equipe')
    
    if request.method == 'POST':
        form = EquipeForm(request.POST, request.FILES, instance=equipe)
        if form.is_valid():
            form.save()
            messages.success(request, f"L'équipe '{equipe.nom}' a été modifiée avec succès.")
            return redirect('equipes:gestion_equipe')
        else:
            messages.error(request, "Erreur lors de la modification. Vérifiez les informations saisies.")
    else:
        form = EquipeForm(instance=equipe)
    
    context = {
        'form': form,
        'equipe': equipe,
    }
    return render(request, 'equipes/modifier_equipe.html', context)

@login_required
def supprimer_equipe(request, equipe_id):
    """
    Vue pour supprimer une équipe complète.
    """
    equipe = get_object_or_404(Equipe, id=equipe_id)
    
    # Vérifier que l'utilisateur est le responsable de cette équipe
    if not equipe.responsable or equipe.responsable.user != request.user:
        return redirect('equipes:gestion_equipe')
    
    if request.method == 'POST':
        nom_equipe = equipe.nom
        equipe.delete()
        logger.info(f"Équipe supprimée: {nom_equipe} par {request.user.username}")
        messages.success(request, f"L'équipe '{nom_equipe}' a été supprimée avec succès", extra_tags='alert-success')
        return redirect('equipes:gestion_equipe')
    
    context = {
        'equipe': equipe,
        'membres_count': MembreEquipe.objects.filter(equipe=equipe).count()
    }
    
    return render(request, 'equipes/confirmer_suppression_equipe.html', context)

@login_required
def supprimer_membre(request, id):
    """
    Vue pour supprimer un membre d'une équipe.
    """
    if request.user.type != 'responsable':
        return redirect('home')
    
    try:
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous n'avez pas d'équipe")
            return redirect('equipes:gestion_equipe')
        
        # Récupérer le membre à supprimer et vérifier qu'il appartient à cette équipe
        membre = get_object_or_404(MembreEquipe, id=id, equipe=equipe)
        
        # Récupérer le nom pour le message de confirmation
        nom_utilisateur = membre.utilisateur.get_full_name() or membre.utilisateur.username
        
        # Supprimer le membre
        membre.delete()
        
        messages.success(request, f"{nom_utilisateur} a été retiré de votre équipe avec succès")
        
    except MembreEquipe.DoesNotExist:
        messages.error(request, "Ce membre n'existe pas ou ne fait pas partie de votre équipe")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la suppression : {str(e)}")
    
    return redirect('equipes:gestion_equipe')

@login_required
def modifier_membre(request, id):
    """
    Vue pour modifier les informations d'un membre d'une équipe.
    """
    if request.user.type != 'responsable':
        return redirect('home')
    
    try:
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            messages.error(request, "Vous n'avez pas d'équipe")
            return redirect('equipes:gestion_equipe')
        
        # Récupérer le membre à modifier et vérifier qu'il appartient à cette équipe
        membre = get_object_or_404(MembreEquipe, id=id, equipe=equipe)
        
        if request.method == 'POST':
            # Ne passer que la position dans le POST data
            position = request.POST.get('position', '')
            membre.position = position if position else None
            membre.save()
            
            nom_utilisateur = membre.utilisateur.get_full_name() or membre.utilisateur.username
            messages.success(request, f"La position de {nom_utilisateur} a été mise à jour avec succès")
            return redirect('equipes:gestion_equipe')
        
        # Pour GET, on prépare juste le contexte avec les choix de position
        context = {
            'membre': membre,
            'equipe': equipe,
            'page_title': f'Modifier {membre.utilisateur.username}',
            'positions_choices': MembreEquipe.POSITIONS_CHOICES,
        }
        
        return render(request, 'equipes/modifier_membre.html', context)
    
    except MembreEquipe.DoesNotExist:
        messages.error(request, "Ce membre n'existe pas ou ne fait pas partie de votre équipe.")
        return redirect('equipes:gestion_equipe')
    except Exception as e:
        messages.error(request, f"Une erreur inattendue est survenue : {str(e)}")
        return redirect('equipes:gestion_equipe')

@login_required
def liste_equipes(request):
    """
    Vue pour afficher la liste de toutes les équipes.
    """
    equipes = Equipe.objects.all().order_by('-date_creation')
    
    # Ajouter des statistiques pour chaque équipe
    equipes_avec_stats = []
    for equipe in equipes:
        equipe.membres_count = MembreEquipe.objects.filter(equipe=equipe).count()
        equipes_avec_stats.append(equipe)
    
    context = {
        'equipes': equipes_avec_stats,
        'total_equipes': equipes.count()
    }
    
    return render(request, 'equipes/liste_equipes.html', context)

@login_required
def detail_equipe(request, equipe_id):
    try:
        equipe = Equipe.objects.get(pk=equipe_id)
    except Equipe.DoesNotExist:
        messages.error(request, "L'équipe demandée n'existe pas.")
        return redirect('home')
    
    # Vérifier si l'utilisateur a le droit de voir cette équipe
    est_responsable = False
    if equipe.responsable and equipe.responsable.user == request.user:
        est_responsable = True
    
    # Vérifier si l'utilisateur est membre de l'équipe
    is_membre = MembreEquipe.objects.filter(equipe=equipe, utilisateur=request.user).exists()
    
    if not (est_responsable or is_membre):
        messages.error(request, "Vous n'avez pas accès à cette équipe.")
        return redirect('home')
    
    # Récupérer les membres avec des détails supplémentaires
    membres = MembreEquipe.objects.filter(equipe=equipe).select_related('utilisateur').order_by('position', 'date_ajout')
    
    # Calculer les statistiques des positions
    positions_stats = _get_positions_stats(membres)
    
    # Calculer des statistiques supplémentaires
    stats = {
        'total_membres': membres.count(),
        'nouvelles_recrues': membres.filter(is_new=True).count(),
        'membres_par_position': positions_stats,
        'date_derniere_modification': equipe.membres.order_by('-date_ajout').first().date_ajout if membres else equipe.date_creation,
    }
    
    # Récupérer les matchs à venir (si le module tournois est disponible)
    matchs_a_venir = []
    try:
        from tournois.models import MatchTournoi
        from django.utils import timezone
        matchs_a_venir = MatchTournoi.objects.filter(
            equipe_domicile=equipe,
            date_match__gt=timezone.now()
        ).order_by('date_match')[:3]
    except:
        # Si le module tournois n'est pas disponible, ignorer cette partie
        pass
    
    context = {
        'equipe': equipe,
        'membres': membres,
        'est_responsable': est_responsable,
        'est_membre': is_membre,
        'stats': stats,
        'matchs_a_venir': matchs_a_venir,
        'page_title': f'Équipe {equipe.nom}',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Mon équipe', 'url': None}
        ]
    }
    
    return render(request, 'equipes/detail_equipe.html', context)

@login_required
def creer_equipe(request):
    # Vérifier si l'utilisateur est un responsable
    if request.user.type != 'responsable':
        return redirect('home')

    # Tenter de récupérer le profil responsable de l'utilisateur
    user_responsable_profile = None
    if hasattr(request.user, 'responsable_profile'):
        try:
            user_responsable_profile = request.user.responsable_profile
        except Responsable.DoesNotExist:
            # Le profil n'existe pas encore, ce qui est attendu si l'utilisateur crée sa première équipe
            pass # user_responsable_profile reste None

    # Vérifier si le responsable a déjà une équipe via le profil récupéré
    if user_responsable_profile and hasattr(user_responsable_profile, 'equipe_geree') and user_responsable_profile.equipe_geree:
        messages.warning(request, "Vous gérez déjà une équipe.")
        return redirect('equipes:gestion_equipe')

    if request.method == 'POST':
        form = EquipeForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Créer ou récupérer le profil responsable si inexistant
                    # Cette étape est maintenant gérée au début de la vue, mais on s'assure qu'on a l'objet
                    responsable_obj, created = Responsable.objects.get_or_create(user=request.user)

                    # Créer l'équipe
                    equipe = form.save(commit=False)
                    equipe.responsable = responsable_obj # Utiliser l'objet responsable créé/récupéré
                    equipe.save()
                    
                    # Ajouter le responsable comme premier membre
                    MembreEquipe.objects.create(equipe=equipe, utilisateur=request.user, position='Responsable')
                    
                    messages.success(request, "Votre équipe a été créée avec succès !")
                    return redirect('equipes:detail_equipe', equipe_id=equipe.pk)
                    
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création de l'équipe : {str(e)}")
    else:
        form = EquipeForm()
    
    context = {
        'form': form,
        'responsable': user_responsable_profile,
        'page_title': 'Créer une équipe',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Création d\'équipe', 'url': None}
        ]
    }
    
    return render(request, 'equipes/creer_equipe.html', context)

@login_required
def api_modifier_membre_position(request, membre_id):
    """
    API pour modifier la position d'un membre via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    if request.user.type != 'responsable':
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    try:
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            return JsonResponse({'success': False, 'error': 'Équipe non trouvée'})
            
        membre = get_object_or_404(MembreEquipe, id=membre_id, equipe=equipe)
        
        nouvelle_position = request.POST.get('position', '')
        membre.position = nouvelle_position if nouvelle_position else None
        membre.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Position de {membre.utilisateur.username} mise à jour'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la modification du membre: {e}")
        return JsonResponse({'success': False, 'error': 'Erreur interne'})

def _get_positions_stats(membres):
    """
    Fonction utilitaire pour calculer les statistiques des positions.
    """
    positions = {}
    for membre in membres:
        position = membre.position or 'Non définie'
        positions[position] = positions.get(position, 0) + 1
    return positions

def envoyer_invitation_email(request, equipe, user, password):
    """
    Fonction utilitaire pour envoyer un email d'invitation à un membre.
    Séparée pour une meilleure réutilisation et lisibilité du code.
    """
    try:
        # Logging au début de la fonction
        logger.info(f"Tentative d'envoi d'email à {user.email} pour l'équipe {equipe.nom}")
        
        # Construire les URLs nécessaires
        login_url = request.build_absolute_uri(reverse('login'))
        equipe_url = request.build_absolute_uri(reverse('equipes:detail_equipe', args=[equipe.id]))
        
        # Contexte pour le template d'email
        context = {
            'equipe': equipe,
            'username': user.username,
            'password': password,
            'login_url': login_url,
            'equipe_url': equipe_url,
            'responsable': equipe.responsable.user.get_full_name() or equipe.responsable.user.username,
            'date_envoi': timezone.now().strftime("%d/%m/%Y"),
        }
        
        # Logging des variables importantes
        logger.info(f"Variables email pour {user.email}: login_url={login_url}, equipe_url={equipe_url}")
        
        # Préparer l'email
        subject = f"Invitation à rejoindre l'équipe {equipe.nom}"
        html_message = render_to_string('responsables/email_invitation_membre.html', context)
        
        # Optimiser le format du texte brut
        plain_message = f"""
Bonjour,

Vous avez été invité à rejoindre l'équipe {equipe.nom} par {context['responsable']}.

Vos identifiants de connexion sont :
- Nom d'utilisateur : {user.username}
- Mot de passe : {password}

Vous pouvez vous connecter ici : {login_url}

Une fois connecté, n'oubliez pas de changer votre mot de passe.

Équipe : {equipe.nom}
URL de l'équipe : {equipe_url}

Cordialement,
L'équipe de gestion des tournois
        """
        
        # Logging avant l'envoi
        logger.info(f"Envoi d'email à {user.email} en cours...")
        
        # Envoyer l'email avec plus de détails en cas d'erreur
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            # Journaliser le succès
            logger.info(f"Email d'invitation envoyé avec succès à {user.email} pour l'équipe {equipe.nom}")
            return True, "Email envoyé avec succès"
            
        except Exception as mail_error:
            # Journaliser l'erreur spécifique d'envoi
            logger.error(f"Erreur lors de l'envoi de l'email à {user.email}: {str(mail_error)}")
            return False, f"Erreur d'envoi: {str(mail_error)}"
            
    except Exception as e:
        # Journaliser l'erreur générale
        logger.error(f"Erreur générale lors de la préparation de l'email pour {user.email}: {str(e)}")
        return False, f"Erreur de préparation: {str(e)}"

@login_required
def ajout_rapide_membre(request, equipe_id):
    """
    Vue simplifiée pour ajouter rapidement un membre à l'équipe.
    """
    # Vérifier si l'utilisateur est le responsable de l'équipe
    equipe = get_object_or_404(Equipe, id=equipe_id)
    
    if not equipe.responsable or equipe.responsable.user != request.user:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette section", extra_tags='alert-danger')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            position = request.POST.get('position', '')
            
            if not email:
                messages.error(request, "L'adresse email est requise", extra_tags='alert-danger')
                return redirect('equipes:detail_equipe', equipe_id=equipe_id)
            
            # Vérifier si l'équipe a atteint sa limite de membres
            if equipe.est_complete():
                messages.error(request, "L'équipe a atteint sa limite de 20 membres", extra_tags='alert-danger')
                return redirect('equipes:detail_equipe', equipe_id=equipe_id)
            
            # Vérifier si l'utilisateur existe déjà
            user = CustomUser.objects.filter(email=email).first()
            
            if user:
                # Vérifier si l'utilisateur est déjà membre de l'équipe
                if MembreEquipe.objects.filter(equipe=equipe, utilisateur=user).exists():
                    messages.warning(request, f"{user.username} est déjà membre de votre équipe", extra_tags='alert-warning')
                    return redirect('equipes:detail_equipe', equipe_id=equipe_id)
                
                # Ajouter l'utilisateur existant à l'équipe
                membre = MembreEquipe.objects.create(
                    equipe=equipe,
                    utilisateur=user,
                    position=position,
                    is_new=True
                )
                
                messages.success(request, f"{user.username} a été ajouté à votre équipe avec succès", extra_tags='alert-success')
                return redirect('equipes:detail_equipe', equipe_id=equipe_id)
            else:
                # Créer un nouvel utilisateur
                try:
                    temp_password = get_random_string(12)
                    username = email.split('@')[0]
                    base_username = username
                    counter = 1
                    
                    # S'assurer que le username est unique
                    while CustomUser.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Créer l'utilisateur avec gestion d'erreur
                    try:
                        new_user = CustomUser.objects.create_user(
                            username=username,
                            email=email,
                            password=temp_password,
                            type='participant',
                            is_active=True
                        )
                        
                        # Créer le membre
                        membre = MembreEquipe.objects.create(
                            equipe=equipe,
                            utilisateur=new_user,
                            position=position,
                            is_new=True
                        )
                        
                        # Envoyer un email avec les identifiants
                        email_success, email_message = envoyer_invitation_email(request, equipe, new_user, temp_password)
                        
                        if email_success:
                            messages.success(
                                request, 
                                f"Un compte a été créé pour {email} et un email d'invitation a été envoyé", 
                                extra_tags='alert-success'
                            )
                        else:
                            logger.warning(f"Échec de l'envoi d'email à {email}: {email_message}")
                            messages.warning(
                                request, 
                                f"Le membre a été ajouté mais l'email n'a pas pu être envoyé. Raison : {email_message}", 
                                extra_tags='alert-warning'
                            )
                        
                    except Exception as user_error:
                        logger.error(f"Erreur lors de la création du compte pour {email}: {str(user_error)}")
                        messages.error(request, f"Erreur lors de la création du compte: {str(user_error)}", extra_tags='alert-danger')
                        return redirect('equipes:detail_equipe', equipe_id=equipe_id)
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'ajout du membre {email}: {str(e)}")
                    messages.error(request, f"Une erreur est survenue: {str(e)}", extra_tags='alert-danger')
                    
                return redirect('equipes:detail_equipe', equipe_id=equipe_id)
        
        except Exception as general_error:
            logger.error(f"Erreur générale dans ajout_rapide_membre: {str(general_error)}")
            messages.error(request, f"Une erreur inattendue est survenue: {str(general_error)}", extra_tags='alert-danger')
            return redirect('equipes:detail_equipe', equipe_id=equipe_id)
    
    # Si ce n'est pas une requête POST, rediriger vers la page de détail de l'équipe
    return redirect('equipes:detail_equipe', equipe_id=equipe_id)

@login_required
def api_verifier_email(request):
    """
    API pour vérifier si un email existe déjà et retourner des informations sur l'utilisateur.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    if request.user.type != 'responsable':
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    email = request.POST.get('email', '')
    if not email:
        return JsonResponse({'success': False, 'error': 'Email requis'})
    
    try:
        # Vérifier si l'utilisateur existe
        user = CustomUser.objects.filter(email=email).first()
        
        # Récupérer l'équipe du responsable
        equipe = get_equipe_responsable(request.user)
        if not equipe:
            return JsonResponse({'success': False, 'error': 'Équipe non trouvée'})
        
        if user:
            # Vérifier si l'utilisateur est déjà membre de l'équipe
            is_member = MembreEquipe.objects.filter(equipe=equipe, utilisateur=user).exists()
            
            return JsonResponse({
                'success': True,
                'exists': True,
                'is_member': is_member,
                'username': user.username,
                'full_name': user.get_full_name(),
                'user_type': user.type,
                'message': 'Cet utilisateur existe déjà dans le système.'
            })
        else:
            # Suggérer un nom d'utilisateur basé sur l'email
            suggested_username = email.split('@')[0]
            counter = 1
            
            while CustomUser.objects.filter(username=suggested_username).exists():
                suggested_username = f"{email.split('@')[0]}{counter}"
                counter += 1
            
            return JsonResponse({
                'success': True,
                'exists': False,
                'suggested_username': suggested_username,
                'message': 'Un nouveau compte sera créé pour cet utilisateur.'
            })
            
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'email {email}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def test_envoi_email(request):
    """
    Vue de test pour vérifier la configuration email.
    Accessible uniquement par les administrateurs ou les responsables.
    """
    if request.user.type not in ['responsable', 'admin']:
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette page", extra_tags='alert-danger')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            email_test = request.POST.get('email_test', '')
            
            if not email_test:
                email_test = request.user.email
                
            # Préparer l'email de test
            subject = "Test d'envoi d'email - Gestion Tournoi"
            message = f"""
            Bonjour,
            
            Ceci est un email de test envoyé depuis l'application de gestion de tournois.
            
            Si vous recevez cet email, cela signifie que la configuration email fonctionne correctement.
            
            Date et heure d'envoi: {timezone.now().strftime("%d/%m/%Y %H:%M:%S")}
            
            Cordialement,
            L'équipe de gestion des tournois
            """
            
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
                <h2 style="color: #0d6efd;">Test d'envoi d'email</h2>
                <p>Bonjour,</p>
                <p>Ceci est un email de test envoyé depuis l'application de gestion de tournois.</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #0d6efd;">
                    <p><strong>Si vous recevez cet email, cela signifie que la configuration email fonctionne correctement.</strong></p>
                </div>
                <p>Date et heure d'envoi: <strong>{timezone.now().strftime("%d/%m/%Y %H:%M:%S")}</strong></p>
                <p>Cordialement,<br>L'équipe de gestion des tournois</p>
            </div>
            """
            
            # Enregistrer la tentative dans les logs
            logger.info(f"Tentative d'envoi d'email de test à {email_test}")
            
            # Envoyer l'email
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email_test],
                    html_message=html_message,
                    fail_silently=False
                )
                
                logger.info(f"Email de test envoyé avec succès à {email_test}")
                messages.success(request, f"Email de test envoyé avec succès à {email_test}. Vérifiez votre boîte de réception.", extra_tags='alert-success')
                
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email de test à {email_test}: {str(e)}")
                messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}", extra_tags='alert-danger')
                
        except Exception as e:
            logger.error(f"Erreur générale lors du test d'email: {str(e)}")
            messages.error(request, f"Une erreur est survenue: {str(e)}", extra_tags='alert-danger')
    
    # Informations sur la configuration email actuelle
    email_config = {
        'EMAIL_BACKEND': settings.EMAIL_BACKEND,
        'EMAIL_HOST': settings.EMAIL_HOST,
        'EMAIL_PORT': settings.EMAIL_PORT,
        'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'EMAIL_TIMEOUT': getattr(settings, 'EMAIL_TIMEOUT', 'Non défini'),
    }
    
    context = {
        'email_config': email_config,
        'user_email': request.user.email,
    }
    
    return render(request, 'equipes/test_email.html', context)

def responsable_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez vous connecter pour accéder à cette page.", extra_tags='login_required')
            # Store the current URL in the session to redirect back after login
            request.session['next_url'] = request.get_full_path()
            return redirect('accounts:login')
        elif request.user.type != 'responsable':
            messages.error(request, "Accès réservé aux responsables d'équipe.", extra_tags='access_denied')
            # Always redirect to home instead of a specific dashboard to avoid loops
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def organisateur_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez vous connecter pour accéder à cette page.", extra_tags='login_required')
            # Store the current URL in the session to redirect back after login
            request.session['next_url'] = request.get_full_path()
            return redirect('accounts:login')
        elif request.user.type != 'organisateur':
            messages.error(request, "Accès réservé aux organisateurs.", extra_tags='access_denied')
            # Always redirect to home instead of a specific dashboard to avoid loops
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def participant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez vous connecter pour accéder à cette page.", extra_tags='login_required')
            # Store the current URL in the session to redirect back after login
            request.session['next_url'] = request.get_full_path()
            return redirect('accounts:login')
        elif request.user.type != 'participant':
            messages.error(request, "Accès réservé aux participants.", extra_tags='access_denied')
            # Always redirect to home instead of a specific dashboard to avoid loops
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper