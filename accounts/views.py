from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import (
    authenticate, login, logout, get_user_model, 
    update_session_auth_hash, forms as auth_forms
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.db.models import Q, Count, Sum, F, Case, When, Prefetch, IntegerField
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .forms import RegisterForm, ProfileForm, AvatarForm, DeleteAccountForm, CustomPasswordResetForm, LoginForm, CustomUserCreationForm
from .models import Profile, NotificationPreference
from equipes.models import Equipe, Responsable, MembreEquipe
from equipes.forms import EquipeForm
from matchs.models import Match
from tournois.models import Tournoi
import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from datetime import datetime
import logging
import json
from django import forms
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.contrib.sites.shortcuts import get_current_site
from django.utils.crypto import get_random_string
from utils.redirects import redirect_by_user_type
from django.middleware.csrf import get_token
from django.utils.translation import gettext as _
from django.views.generic import CreateView, UpdateView
from django.utils.decorators import method_decorator

# Configurer le logger
logger = logging.getLogger(__name__)

User = get_user_model()

def home(request):
    """Vue pour la page d'accueil"""
    logger.info("Affichage de la page d'accueil")
    
    # Si l'utilisateur est connecté, le rediriger vers son tableau de bord
    if request.user.is_authenticated:
        # Vérifier si nous sommes dans une boucle de redirection potentielle
        redirect_count = request.session.get('redirect_count', 0)
        if redirect_count >= 2:  # Si on a déjà redirigé plusieurs fois
            logger.error(f"Boucle de redirection détectée dans home view, affichage direct de la liste des tournois")
            request.session['redirect_count'] = 0  # Reset le compteur
            messages.warning(request, "Redirection vers la liste des tournois pour éviter une boucle.")
            # Redirigeons vers une page sûre qui n'entraîne pas de redirections supplémentaires
            return redirect('tournois:liste')
        
        # Redirection normale basée sur le type d'utilisateur
        return redirect_by_user_type(request)
    
    # Récupérer quelques données pour la page d'accueil
    try:
        tournois_en_cours = Tournoi.objects.filter(
            date_debut__lte=timezone.now().date(),
            date_fin__gte=timezone.now().date() if Tournoi._meta.get_field('date_fin') else None
        ).order_by('-date_debut')[:5]
        
        tournois_a_venir = Tournoi.objects.filter(
            date_debut__gt=timezone.now().date()
        ).order_by('date_debut')[:5]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tournois: {e}")
        # En cas d'erreur, simplement utiliser des listes vides
        tournois_en_cours = []
        tournois_a_venir = []
    
    context = {
        'tournois_en_cours': tournois_en_cours,
        'tournois_a_venir': tournois_a_venir,
    }
    
    # Rendre la template directement sans passer par d'autres redirections
    return render(request, 'tournois/home.html', context)


def login_view(request):
    """Vue de connexion pour les utilisateurs."""
    logger.error(f"==== LOGIN VIEW ENTRY ====")
    logger.error(f"Session ID: {request.session.session_key}")
    logger.error(f"User authenticated: {request.user.is_authenticated}")
    
    # Si l'utilisateur est déjà connecté, le rediriger vers la page appropriée
    if request.user.is_authenticated:
        return redirect_by_user_type(request)
    
    # Récupérer l'URL de redirection après connexion
    next_url = request.GET.get('next', '')
    if not next_url and 'next_url' in request.session:
        next_url = request.session.get('next_url', '')
        # Nettoyer la session une fois utilisée
        if 'next_url' in request.session:
            del request.session['next_url']
    
    # S'assurer que le jeton CSRF est généré pour cette vue
    csrf_token = get_token(request)
    logger.error(f"CSRF Token généré: {csrf_token}")
            
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember = form.cleaned_data.get('remember')
            
            logger.error(f"Login attempt for username: {username}")
            
            user = authenticate(request, username=username, password=password)
            
            logger.error(f"Authentication result: {user is not None}")
            
            if user is not None:
                login(request, user)
                
                logger.error(f"User logged in: {user.username}")
                logger.error(f"User type: {user.type}")
                logger.error(f"Session after login: {dict(request.session)}")
                
                if not remember:
                    # Si l'utilisateur ne coche pas "Se souvenir de moi",
                    # on configure la session pour qu'elle expire à la fermeture du navigateur
                    request.session.set_expiry(0)
                
                # Rediriger vers l'URL next si présente et valide
                if next_url:
                    return redirect(next_url)
                
                # Rediriger en fonction du type d'utilisateur
                if user.type == 'organisateur':
                    logger.error(f"Redirecting to organisateurs:dashboard")
                    return redirect('organisateurs:dashboard')
                elif user.type == 'responsable':
                    return redirect('responsables:tableau_bord')
                elif user.type == 'participant':
                    return redirect('participants:tableau_bord')
                else:
                    return redirect('home')
            else:
                logger.error(f"Authentication failed for username: {username}")
                messages.error(request, _("Email ou mot de passe incorrect."))
        else:
            logger.error(f"Form validation errors: {form.errors}")
            messages.error(request, _("Veuillez corriger les erreurs dans le formulaire."))
    else:
        logger.error(f"GET request to login_view")
        form = LoginForm()
    
    return render(request, 'registration/login.html', {
        'form': form,
        'next': next_url
    })


@require_http_methods(["GET", "POST"])
def register(request):
    """Vue pour gérer l'inscription des utilisateurs"""
    if request.user.is_authenticated:
        return redirect('home')
    
    # S'assurer que le jeton CSRF est généré pour cette vue
    csrf_token = get_token(request)
    logger.error(f"CSRF Token généré pour inscription: {csrf_token}")
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        
        if not request.POST.get('agreeTerms'):
            messages.error(request, 'Vous devez accepter les conditions d\'utilisation.')
            return render(request, 'registration/register.html', {'form': form})
        
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                # Le signal post_save s'occupera de créer le profil
            
            messages.success(request, 'Compte créé avec succès! Vous pouvez maintenant vous connecter.')
            return redirect('accounts:login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def logout_view(request):
    """Vue pour gérer la déconnexion des utilisateurs"""
    logger.info("=== Début de la vue de déconnexion ===")
    logger.info(f"Utilisateur actuel: {request.user}")
    logger.info(f"Session key: {request.session.session_key}")
    
    user = request.user
    # Ajout du nettoyage de la session avant la déconnexion
    request.session.flush()
    logout(request)
    logger.info(f"Utilisateur {user} déconnecté")
    
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    logger.info("=== Fin de la vue de déconnexion ===")
    
    # Rediriger vers la page d'accueil avec un paramètre pour éviter la mise en cache
    # et forcer une nouvelle requête sans les cookies de session précédents
    redirect_url = f"{reverse('home')}?logout={get_random_string(8)}"
    return redirect(redirect_url)


@login_required
def profile_view(request):
    """
    Vue simplifiée pour afficher le profil utilisateur.
    Ne gère que les informations d'authentification (username et email).
    """
    user = request.user
    profile_form = ProfileForm(instance=user.profile)
    password_form = auth_forms.PasswordChangeForm(user=user)
    delete_account_form = DeleteAccountForm()
    
    context = {
        'user': user,
        'profile': user.profile,
        'form': profile_form,
        'password_form': password_form,
        'delete_account_form': delete_account_form,
        'user_type': user.type,
    }
    
    # Gestion des formulaires POST
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # Mapping des handlers de formulaire
        form_handlers = {
            'profile': handle_profile_update,
            'avatar': handle_avatar_update,
            'delete_account': handle_account_deletion,
            'change_password': handle_change_password,
        }
        
        handler = form_handlers.get(form_type)
        if handler:
            result = handler(request, user, user.profile)
            if result and result.get('redirect'):
                return result['redirect']
            if result and result.get('form_processed'):
                if result.get('form_message'):
                    if result.get('form_status') == 'success':
                        messages.success(request, result['form_message'])
                    elif result.get('form_status') == 'warning':
                        messages.warning(request, result['form_message'])
                    else:
                        messages.error(request, result['form_message'])
    
    # Déterminer l'onglet actif à partir des paramètres de requête
    active_tab = request.GET.get('tab', 'profile')
    context['active_tab'] = active_tab
    
    return render(request, 'registration/profile.html', context)


def handle_profile_update(request, user, profile):
    """Gestion de la mise à jour du profil"""
    try:
        # Utilisation d'un formulaire pour la validation
        form = ProfileForm(request.POST, request.FILES, instance=profile) # Ensure request.FILES is included for avatar
        print(f"DEBUG: handle_profile_update - form received: {form}")

        if form.is_valid():
            print("DEBUG: handle_profile_update - Form is valid.")
            # Transaction pour garantir l'intégrité
            with transaction.atomic():
                # Mise à jour de l'utilisateur
                user.first_name = form.cleaned_data.get('first_name', user.first_name) # Use .get with default to avoid KeyError
                user.last_name = form.cleaned_data.get('last_name', user.last_name) # Use .get with default to avoid KeyError
                user.save(update_fields=['first_name', 'last_name'])
                print("DEBUG: handle_profile_update - User saved.")

                # Sauvegarde du profil
                profile = form.save() # Save returns the instance
                print("DEBUG: handle_profile_update - Profile saved.")

            success_message = 'Votre profil a été mis à jour avec succès!'
            print(f"DEBUG: handle_profile_update - Returning success: {success_message}")
            return {
                'form_processed': True,
                'form_status': 'success',
                'form_message': success_message,
                'form_type': 'profile'
            }
        else:
            print("DEBUG: handle_profile_update - Form is NOT valid.")
            print(f"DEBUG: handle_profile_update - Form errors: {form.errors}")
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            full_error_message = 'Veuillez corriger les erreurs suivantes: ' + ', '.join(error_messages)
            print(f"DEBUG: handle_profile_update - Returning danger: {full_error_message}")
            return {
                'form_processed': True,
                'form_status': 'danger',
                'form_message': full_error_message,
                'form_type': 'profile'
            }
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du profil pour l'utilisateur {user.email}: {str(e)}")
        print(f"DEBUG: handle_profile_update - Caught exception: {str(e)}")
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': f"Une erreur s'est produite: {str(e)}",
            'form_type': 'profile'
        }


def handle_avatar_update(request, user, profile):
    """Gestion de la mise à jour de l'avatar"""
    try:
        form = AvatarForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid() and 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            
            # Vérifications et optimisation de l'image
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = os.path.splitext(avatar_file.name)[1].lower()
            
            if ext not in valid_extensions:
                raise ValidationError("Format d'image non supporté. Utilisez JPG, PNG ou GIF.")
                
            if avatar_file.size > 2 * 1024 * 1024:  # Réduction à 2MB max
                raise ValidationError("L'image ne doit pas dépasser 2MB.")
            
            # Traitement de l'image
            img = Image.open(avatar_file)
            max_size = (600, 600)  # Réduction de la taille maximale
            
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Format de sortie optimisé
            output_format = 'PNG' if ext == '.png' else 'JPEG'
            output = BytesIO()
            
            if output_format == 'JPEG':
                img.save(output, format=output_format, quality=80, optimize=True)
            else:
                img.save(output, format=output_format, optimize=True)
            
            output.seek(0)
            
            # Création du fichier optimisé
            optimized_avatar = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{os.path.splitext(avatar_file.name)[0]}_optimized{ext}",
                f'image/{output_format.lower()}',
                sys.getsizeof(output),
                None
            )
            
            # Suppression de l'ancien avatar si existant
            if profile.avatar:
                try:
                    old_path = profile.avatar.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    # Log l'erreur mais continue le processus
                    logger.warning(f"Erreur de suppression d'avatar: {e}")
            
            # Sauvegarde du nouvel avatar
            profile.avatar = optimized_avatar
            profile.save(update_fields=['avatar'])
            
            return {
                'form_processed': True,
                'form_status': 'success',
                'form_message': 'Votre avatar a été mis à jour avec succès!',
                'form_type': 'avatar'
            }
        else:
            if 'avatar' not in request.FILES:
                raise ValidationError("Aucune image n'a été sélectionnée.")
            raise ValidationError(form.errors.as_text())
    
    except ValidationError as e:
        return {
            'form_processed': True,
            'form_status': 'warning',
            'form_message': str(e),
            'form_type': 'avatar'
        }
    except Exception as e:
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': f"Une erreur s'est produite: {str(e)}",
            'form_type': 'avatar'
        }


def handle_account_deletion(request, user, profile):
    """Gestion de la suppression de compte"""
    try:
        form = DeleteAccountForm(request.POST)
        
        if form.is_valid():
            password = form.cleaned_data['password']
            confirm_delete = form.cleaned_data['confirm_delete']
            
            if not confirm_delete:
                raise ValidationError("Vous devez confirmer la suppression de votre compte.")
            
            if not user.check_password(password):
                raise ValidationError("Mot de passe incorrect. La suppression du compte a échoué.")
            
            email = user.email
            
            # Suppression de l'utilisateur dans une transaction atomique
            with transaction.atomic():
                user.delete()
            
            messages.success(request, f"Le compte associé à {email} a été supprimé avec succès.")
            return {'redirect': redirect('home')}
        else:
            raise ValidationError(form.errors.as_text())
    
    except ValidationError as e:
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': str(e),
            'form_type': 'security'
        }
    except Exception as e:
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': f"Une erreur s'est produite: {str(e)}",
            'form_type': 'security'
        }


def handle_create_team(request, user, profile):
    """Gestion de la création d'une équipe depuis le profil."""
    try:
        form = EquipeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                team = form.save(commit=False)
                team.createur = user  # Assigner l'utilisateur créateur
                team.save()
                # Ajouter le créateur comme membre initial de l'équipe (si nécessaire)
                MembreEquipe.objects.create(equipe=team, utilisateur=user, role='manager')  # Exemple de rôle

            return {
                'form_processed': True,
                'form_status': 'success',
                'form_message': f"L'équipe \"{team.nom}\" a été créée avec succès !",
                'form_type': 'create_team'
            }
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")

            # Passer le formulaire au contexte pour afficher les erreurs dans le modal
            return {
                'form_processed': True,
                'form_status': 'danger',
                'form_message': f'Veuillez corriger les erreurs suivantes lors de la création de l\'équipe: {", ".join(error_messages)}',
                'form_type': 'create_team',
                'team_form': form  # Passer le formulaire au contexte
            }

    except Exception as e:
        logger.error(f"Erreur lors de la création d'équipe pour l'utilisateur {user.email}: {str(e)}")
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': f"Une erreur est survenue lors de la création de l'équipe: {str(e)}",
            'form_type': 'create_team'
        }


def handle_change_password(request, user, profile):
    """Gestion du changement de mot de passe depuis le profil."""
    try:
        # Récupérer les données du formulaire
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validation de base
        if not old_password or not new_password1 or not new_password2:
            raise ValidationError("Tous les champs sont requis.")
            
        if new_password1 != new_password2:
            raise ValidationError("Les nouveaux mots de passe ne correspondent pas.")
            
        # Vérifier l'ancien mot de passe
        if not user.check_password(old_password):
            raise ValidationError("Le mot de passe actuel est incorrect.")
            
        # Valider la complexité du nouveau mot de passe
        if len(new_password1) < 8:
            raise ValidationError("Le nouveau mot de passe doit contenir au moins 8 caractères.")
            
        # Changer le mot de passe
        user.set_password(new_password1)
        user.save()
        
        # Mettre à jour la session pour éviter la déconnexion
        update_session_auth_hash(request, user)
        
        return {
            'form_processed': True,
            'form_status': 'success',
            'form_message': 'Votre mot de passe a été changé avec succès!',
            'form_type': 'change_password',
            'redirect': redirect(f"{reverse('accounts:profile')}?tab=security&status=success&form=password")
        }
            
    except ValidationError as e:
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': str(e),
            'form_type': 'change_password'
        }
    except Exception as e:
        logger.error(f"Erreur lors du changement de mot de passe pour l'utilisateur {user.email}: {str(e)}")
        return {
            'form_processed': True,
            'form_status': 'danger',
            'form_message': f"Une erreur est survenue lors du changement de mot de passe: {str(e)}",
            'form_type': 'change_password'
        }


@login_required
def dashboard_view(request):
    """
    Vue qui redirige vers le tableau de bord approprié en fonction du rôle de l'utilisateur.
    """
    try:
        # Pour les participants, vérifier s'ils ont des équipes
        user = request.user
        user_type = getattr(user, 'type', None)
        
        # Vérifier si nous sommes dans une boucle de redirection potentielle
        redirect_count = request.session.get('redirect_count', 0)
        if redirect_count >= 2:  # Si on a déjà redirigé plusieurs fois
            logger.error(f"Boucle de redirection détectée dans dashboard_view, affichage direct de la liste des tournois")
            request.session['redirect_count'] = 0  # Reset le compteur
            messages.warning(request, "Redirection vers la liste des tournois pour éviter une boucle.")
            # Redirigeons vers une page sûre qui n'entraîne pas de redirections supplémentaires
            return redirect('tournois:liste')
        
        if user_type == 'participant':
            # Vérifier si le participant a des équipes
            from equipes.models import MembreEquipe
            if not MembreEquipe.objects.filter(utilisateur=user).exists():
                messages.info(
                    request,
                    "Vous n'avez pas encore d'équipe. Consultez les tournois disponibles pour trouver une équipe."
                )
                return redirect('tournois:liste')
        
        # Utiliser notre fonction utilitaire pour rediriger selon le type d'utilisateur
        return redirect_by_user_type(request)
            
    except Exception as e:
        logger.error(f"Erreur de redirection pour l'utilisateur {request.user.email}: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la redirection.")
        return redirect('tournois:liste')


class CustomPasswordResetView(BasePasswordResetView):
    """
    Vue personnalisée pour la réinitialisation du mot de passe.
    """
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passer explicitement le nom d'URL namespacé au contexte pour la balise url dans le template email
        context['url'] = 'accounts:password_reset_confirm' # Utiliser le nom namespacé
        # Conserver l'ajout manuel de uid et token au contexte au cas o le template par dfaut en aurait besoin
        user = context.get('user')
        if user:
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.contrib.auth.tokens import default_token_generator
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            context['uid'] = uid
            context['token'] = token

            # La construction manuelle de reset_url n'est pas ncessaire si on utilise {% url %}
            # dans le template par dfaut et qu'on passe le nom d'URL corrig ici.
            # Je vais la commenter ou la supprimer pour simplifier.
            # from django.urls import reverse
            # from django.contrib.sites.shortcuts import get_current_site
            # site = get_current_site(self.request) if self.request else None
            # protocol = 'https' if self.request and self.request.is_secure() else 'http'
            # try:
            #     path = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            #     if site:
            #         reset_url = f"{protocol}://{site.domain}{path}"
            #     else:
            #         from django.conf import settings
            #         reset_url = f"{protocol}://{settings.SITE_DOMAIN}{path}"
            #     context['reset_url'] = reset_url
            # except Exception as e:
            #      import logging
            #      logger = logging.getLogger(__name__)
            #      logger.error(f"Erreur lors de la construction de l'URL de reset dans get_context_data: {e}")
            #      pass

        return context

    def dispatch(self, request, *args, **kwargs):
        # Si l'utilisateur est déjà connecté, on le redirige vers son profil
        if request.user.is_authenticated:
            messages.info(request, "Vous êtes déjà connecté. Vous pouvez changer votre mot de passe depuis votre profil.", extra_tags='password_reset')
            return redirect('accounts:profile')

        # Si l'utilisateur n'est PAS connecté, on permet l'accès à la vue de réinitialisation
        # La classe parente BasePasswordResetView gère déjà l'accès pour les non-authentifiés par défaut
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Récupère l'email depuis l'URL si présent"""
        initial = super().get_initial()
        email = self.request.GET.get('email')
        if email:
            initial['email'] = email
        return initial

    def form_valid(self, form):
        """Gestion personnalisée du formulaire valide"""
        email = form.cleaned_data['email']
        try:
            # Vérifier si l'utilisateur existe (cette vérification est déjà faite par form.save() dans la classe parente,
            # mais nous pouvons ajouter un message d'avertissement si l'email n'existe pas)
            User = get_user_model()
            user_exists = User.objects.filter(email=email).exists()

            if not user_exists:
                messages.warning(
                    self.request,
                    "Aucun compte n'est associé à cette adresse email.",
                    extra_tags='password_reset'
                )
                # Nous ne retournons pas form_invalid ici pour éviter de perdre le message d'avertissement
                # La méthode form_valid de la classe parente gérera la non-existence de l'email sans erreur visible par l'utilisateur,
                # ce qui est une bonne pratique de sécurité. Nous ajoutons juste le message ici.
                pass # Continuer pour permettre le comportement par défaut qui ne dit pas si l'utilisateur existe ou non

            # Continuer avec le processus normal de réinitialisation de la classe parente
            response = super().form_valid(form)

            # Ajouter un message de succès SEULEMENT si l'email a été envoyé (ce que super().form_valid(form) gère)
            # Django n'envoie l'email que si l'utilisateur existe.
            messages.success(
                self.request,
                "Si un compte est associé à cette adresse email, les instructions de réinitialisation ont été envoyées.",
                extra_tags='password_reset'
            )
            return response

        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation du mot de passe pour {email}: {str(e)}")
            messages.error(
                self.request,
                "Une erreur est survenue lors de l'envoi des instructions. Veuillez réessayer.",
                extra_tags='password_reset'
            )
            return self.form_invalid(form) # Retourner form_invalid en cas d'exception réelle

    def get_success_url(self):
        """URL de redirection après l'envoi réussi"""
        return reverse('accounts:password_reset_done')

@login_required
def notification_preferences(request):
    """Vue pour gérer les préférences de notification"""
    # Récupérer ou créer les préférences de notification
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Mettre à jour les préférences générales
        preferences.enable_all = 'enable_all' in request.POST
        preferences.sound_enabled = 'sound_enabled' in request.POST
        
        # Mettre à jour les préférences par type de notification
        preferences.match_notifications = 'match_notifications' in request.POST
        preferences.tournament_notifications = 'tournament_notifications' in request.POST
        preferences.team_notifications = 'team_notifications' in request.POST
        preferences.result_notifications = 'result_notifications' in request.POST
        
        # Mettre à jour les préférences de livraison
        preferences.email_delivery = 'email_delivery' in request.POST
        preferences.push_delivery = 'push_delivery' in request.POST
        
        # Mettre à jour les préférences de digest
        preferences.digest_enabled = 'digest_enabled' in request.POST
        if 'digest_frequency' in request.POST and request.POST['digest_frequency'] in ['daily', 'weekly']:
            preferences.digest_frequency = request.POST['digest_frequency']
        
        # Sauvegarder les modifications
        preferences.save()
        
        messages.success(request, "Vos préférences de notification ont été mises à jour avec succès.")
        return redirect('accounts:notification_preferences')
    
    context = {
        'preferences': preferences,
        'page_title': 'Préférences de notification',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Mon profil', 'url': 'accounts:profile'},
            {'name': 'Préférences de notification', 'url': None, 'active': True},
        ]
    }
    
    return render(request, 'accounts/notification_preferences.html', context)