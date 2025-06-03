from django.shortcuts import redirect, render
from django.urls import resolve, reverse
from django.conf import settings
from django.contrib import messages
import logging
import time

logger = logging.getLogger(__name__)

class ParticipantAccessMiddleware:
    """
    Middleware spécifique pour gérer les accès et actions des participants.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if user attribute is available and user is authenticated
        try:
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                logger.info(f"Anonymous user or user attribute unavailable accessing {request.path}, skipping ParticipantAccessMiddleware")
                return self.get_response(request)
        except (AttributeError, Exception) as e:
            # Log error and skip this middleware if there's an issue with user detection
            logger.error(f"Error checking user in ParticipantAccessMiddleware: {str(e)}")
            return self.get_response(request)
            
        # Si l'utilisateur n'est pas un participant, passer au middleware suivant
        if getattr(request.user, 'type', None) != 'participant':
            return self.get_response(request)
            
        current_url = request.path
        current_url_name = None
        
        # Vérifier spécifiquement si l'utilisateur tente de se déconnecter
        if current_url == '/logout/':
            return self.get_response(request)
            
        try:
            resolver_match = resolve(current_url)
            current_url_name = resolver_match.url_name
            namespace = resolver_match.namespace
            
            if namespace:
                current_url_name = f"{namespace}:{current_url_name}"
        except Exception as e:
            # Log the error for debugging, but continue
            logger.error(f"Error resolving URL {current_url}: {e}")
            current_url_name = None # Ensure it's None on failure
            
        # URLs autorisées pour les participants (par nom d'URL ou par préfixe de chemin)
        allowed_urls_by_name = {
            'home': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès à la page d'accueil."
            },
            'accounts:profile': {
                'allowed_methods': ['GET', 'POST'],
                'allowed_actions': ['profile', 'avatar'],
                'message': "Vous n'avez pas les permissions nécessaires pour effectuer cette action."
            },
            'tournois:liste': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès à la liste des tournois."
            },
            'tournois:detail': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès aux détails de ce tournoi."
            },
            'equipes:liste_equipes': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès à la liste des équipes."
            },
            'equipes:detail_equipe': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès aux détails de cette équipe."
            },
            'matchs:liste': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès à la liste des matchs."
            },
            'matchs:detail': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès aux détails de ce match."
            },
            'participants:tableau_bord': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès au tableau de bord."
            },
            'participants:voir_calendrier_resultats_participant': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès au calendrier des matchs."
            },
            'participants:voir_matchs_amicaux': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès aux matchs amicaux."
            },
            'participants:voir_tournois_disponibles': {
                'allowed_methods': ['GET'],
                'message': "Vous n'avez pas accès aux tournois disponibles."
            },
            'logout': {
                'allowed_methods': ['GET', 'POST'],
                'message': "Vous n'avez pas les permissions pour vous déconnecter."
            }
        }

        # Liste des préfixes de chemins autorisés pour les participants
        allowed_path_prefixes = [
            '/media/',
            '/static/',
            '/accounts/profile/', # Accès au profil et ses sous-chemins (update, etc.)
            '/participants/',    # Accès au tableau de bord participant et autres urls participants
            '/matchs/',          # Accès aux matchs (lecture seule)
            '/tournois/',        # Accès aux tournois (lecture seule)
            '/equipes/',         # Accès aux équipes (lecture seule)
            '/logout/',          # Accès à la déconnexion
            '/notifications/',   # Accès aux notifications
        ]
        
        # Vérifier si l'URL est autorisée par nom
        is_url_name_allowed = current_url_name is not None and current_url_name in allowed_urls_by_name
        
        # Vérifier si l'URL est autorisée par préfixe de chemin
        is_path_prefix_allowed = any(current_url.startswith(prefix) for prefix in allowed_path_prefixes)
        
        # Si l'URL est autorisée par nom ou par préfixe de chemin
        if is_url_name_allowed:
            permissions = allowed_urls_by_name[current_url_name]

            # Vérifier la méthode HTTP si autorisée par nom
            if request.method not in permissions.get('allowed_methods', ['GET']):
                messages.error(request, f"Méthode {request.method} non autorisée pour {current_url_name}.")
                return redirect('participants:tableau_bord')

            # Vérifier les actions spécifiques pour le profil (si applicable et méthode POST)
            if current_url_name == 'accounts:profile' and request.method == 'POST':
                form_type = request.POST.get('form_type')
                # Si form_type est présent, vérifier qu'il est dans les actions autorisées
                if form_type is not None and form_type not in permissions.get('allowed_actions', []):
                    messages.error(request, permissions.get('message', "Vous n'avez pas les permissions nécessaires pour effectuer cette action sur votre profil."))
                    return redirect('accounts:profile')
                    
            # Si autorisée par nom et a passé les vérifs de méthode/action, laissez passer
            return self.get_response(request)
            
        elif is_path_prefix_allowed:
             # Si non autorisée par nom, mais autorisée par préfixe de chemin, laissez passer
             # Pour la route /tournois/, s'assurer que l'URL est examinée correctement
             if current_url == '/tournois/':
                 # Laissez passer sans redirection pour accéder à la liste des tournois
                 return self.get_response(request)
             return self.get_response(request)
            
        # Si l'URL n'est autorisée ni par nom (avec vérifications) ni par préfixe
        else:
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette section.")
            return redirect('participants:tableau_bord')

class RedirectionLoopProtectionMiddleware:
    """
    Middleware qui détecte et protège contre les boucles de redirection infinies.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.redirects = {}  # Pour stocker les informations de redirection
        self.threshold = 5   # Nombre de redirections maximales autorisées
        self.timeout = 5     # Durée (en secondes) après laquelle les redirections sont réinitialisées
        # Pages exemptées de la vérification de boucle pour utilisateurs anonymes et API
        self.anonymous_exempt_paths = ['/', '/home/', '/index/']
        # API endpoints exemptés des vérifications de redirection
        self.api_exempt_paths = ['/notifications/api/']

    def __call__(self, request):
        # Récupérer l'adresse IP et le chemin pour identifier la redirection
        ip = self.get_client_ip(request)
        path = request.path
        key = f"{ip}:{path}"
        current_time = time.time()
        
        # Check if user is authenticated - handle the case where request.user might not be available
        is_authenticated = False
        try:
            is_authenticated = request.user.is_authenticated
        except AttributeError:
            # Log the error but continue with default anonymous behavior
            logger.error("RedirectionLoopProtectionMiddleware: request.user not available")
        
        # Exempter les pages d'accueil pour les utilisateurs anonymes et les endpoints API
        if (not is_authenticated and path in self.anonymous_exempt_paths) or any(path.startswith(api_path) for api_path in self.api_exempt_paths):
            logger.info(f"Exempting path from redirect loop check: {path}")
            return self.get_response(request)

        # Log les détails de la requête
        logger.error(f"==== REDIRECTION CHECK ==== Path: {path}, IP: {ip}")
        
        # Nettoyer les anciennes entrées
        self.clean_old_entries(current_time)
        
        # Vérifier si cette URL est déjà dans une boucle de redirection
        if key in self.redirects:
            redirect_info = self.redirects[key]
            
            # Incrémenter le compteur
            redirect_info["count"] += 1
            redirect_info["last_time"] = current_time
            
            # Vérifier si le seuil est dépassé
            if redirect_info["count"] > self.threshold:
                logger.error(f"LOOP DETECTED! Path: {path}, Count: {redirect_info['count']}")
                
                # Réinitialiser le compteur
                del self.redirects[key]
                
                # Verify user attribute is available before using it
                user_str = 'Anonymous'
                try:
                    if request.user.is_authenticated:
                        user_str = request.user.username
                except AttributeError:
                    pass
                
                # Afficher une page d'erreur
                error_context = {
                    'title': 'Erreur de redirection',
                    'message': 'Une boucle de redirection a été détectée. Veuillez contacter l\'administrateur.',
                    'details': f"Path: {path}, Redirects: {redirect_info['count']}, User: {user_str}"
                }
                return render(request, 'error.html', error_context)
        else:
            # Première visite de cette URL
            self.redirects[key] = {
                "count": 1,
                "last_time": current_time
            }
        
        # Continuer le traitement de la requête
        response = self.get_response(request)
        
        # Si c'est une redirection, incrémenter le compteur
        if 300 <= response.status_code < 400:
            logger.error(f"REDIRECT DETECTED! From: {path} to: {response.get('Location', 'Unknown')}")
            if key in self.redirects:
                self.redirects[key]["count"] += 1
        
        return response

    def get_client_ip(self, request):
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
        
    def clean_old_entries(self, current_time):
        """Nettoie les entrées plus anciennes que self.timeout"""
        keys_to_delete = []
        for key, info in self.redirects.items():
            if current_time - info["last_time"] > self.timeout:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.redirects[key]

class RoleBasedAccessMiddleware:
    """
    Middleware pour gérer l'accès basé sur les rôles (Organisateur, Responsable, Participant).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Ajouter des logs de débogage ici
        current_url = request.path
        logger.error(f"==== ROLE MIDDLEWARE ==== URL: {current_url}")
        
        # Check safely if user is authenticated
        is_authenticated = False
        try:
            is_authenticated = hasattr(request, 'user') and request.user.is_authenticated
            logger.error(f"User authenticated: {is_authenticated}")
            
            if is_authenticated:
                logger.error(f"User: {request.user.username} (ID: {request.user.id})")
                logger.error(f"User type: {getattr(request.user, 'type', 'N/A')}")
                logger.error(f"Session ID: {request.session.session_key}")
                logger.error(f"Session data: {dict(request.session)}")
        except (AttributeError, Exception) as e:
            logger.error(f"Error checking user in RoleBasedAccessMiddleware: {str(e)}")
            # If we can't verify authentication, proceed with the request
            return self.get_response(request)

        # Autoriser la déconnexion explicitement pour tous les utilisateurs
        if request.path == '/logout/':
            logger.info("URL de déconnexion détectée, autorisation accordée")
            return self.get_response(request)

        # Initialiser current_url_name à None par défaut
        current_url_name = None

        try:
            resolver_match = resolve(current_url)
            current_url_name = resolver_match.url_name
            namespace = resolver_match.namespace
            
            if namespace:
                current_url_name = f"{namespace}:{current_url_name}"
                
            logger.error(f"Resolved URL name: {current_url_name}")
        except Exception as e:
            # Log the error for debugging, but continue
            logger.error(f"Error resolving URL {current_url}: {e}")
            current_url_name = None # Ensure it's None on failure

        # Toujours permettre l'accès aux pages de connexion, inscription, déconnexion et à la page d'accueil.
        public_urls = [
            'login', 
            'register', 
            'logout', 
            'home',
            'privacy',          # Ajouter la page de confidentialité
            'terms',            # Ajouter la page de conditions d'utilisation
            'accounts:login',   # Ajouter l'URL de connexion avec namespace
            'accounts:register',# Ajouter l'URL d'inscription avec namespace
            'accounts:password_reset',          # Ajouter l'URL de demande de rinitialisation
            'accounts:password_reset_done',     # Ajouter l'URL de confirmation de l'envoi de l'email
            'accounts:password_reset_confirm',  # Ajouter l'URL de confirmation du lien de rinitialisation
            'accounts:password_reset_complete', # Ajouter l'URL de confirmation de la rinitialisation complte
        ]
        # Utiliser le nom d'URL 'logout' au lieu de settings.LOGOUT_URL
        public_paths = [
            settings.LOGIN_URL, 
            reverse(settings.LOGIN_URL), 
            reverse('logout'), 
            reverse(settings.LOGOUT_REDIRECT_URL), 
            '/login/', 
            '/register/', 
            '/accounts/register/',
            '/accounts/login/',
            '/logout/', 
            '/', 
            '/privacy/', 
            '/terms/'
        ]
        
        if current_url_name in public_urls or current_url in public_paths or current_url.startswith(('/media/', '/static/')):
            logger.error(f"Public URL allowed: {current_url}")
            return self.get_response(request)

        # Si l'utilisateur n'est pas authentifié et n'accède pas à une page publique, rediriger vers la page de connexion.
        if not request.user.is_authenticated:
            # Stocker l'URL demandée pour y revenir après connexion
            next_url = request.get_full_path()
            request.session['next_url'] = next_url
            logger.error(f"User not authenticated, redirecting to login with next_url={next_url}")
            
            # Message plus précis selon l'URL demandée
            if current_url.startswith('/organisateurs/'):
                messages.error(request, "Vous devez vous connecter en tant qu'organisateur pour accéder à cette section.", extra_tags='login_required')
            elif current_url.startswith('/responsables/'):
                messages.error(request, "Vous devez vous connecter en tant que responsable d'équipe pour accéder à cette section.", extra_tags='login_required')
            elif current_url.startswith('/participants/'):
                messages.error(request, "Vous devez vous connecter en tant que participant pour accéder à cette section.", extra_tags='login_required')
            elif current_url == '/accounts/register/' or current_url == '/register/':
                # Accès direct à la page d'inscription sans redirection pour éviter une boucle infinie
                return self.get_response(request)
            else:
                messages.error(request, "Vous devez vous connecter pour accéder à cette page. Si vous n'avez pas de compte, vous pouvez vous inscrire.", extra_tags='login_required')
                
            return redirect(settings.LOGIN_URL)

        # Si c'est un participant, laisser le ParticipantAccessMiddleware gérer les permissions
        if getattr(request.user, 'type', None) == 'participant':
            logger.error(f"User is participant, passing to ParticipantAccessMiddleware")
            return self.get_response(request)
        
        # Liste des URLs accessibles à tous les utilisateurs authentifiés (non participants)
        unrestricted_urls_authenticated = [
            'home',
            'logout',
            'admin:index',
            'dashboard',
            'accounts:profile',
            'notifications:liste',
            'notifications:detail',
            'notifications:get_notifications_ajax',
            'tournois:liste',
            'tournois:detail',
        ]

        # Si l'URL est une URL non restreinte pour les utilisateurs authentifiés (non participants), laisser passer
        if current_url_name in unrestricted_urls_authenticated or current_url.startswith('/admin/') or current_url == '/' or current_url.startswith('/accounts/profile/') or current_url.startswith('/notifications/') or current_url.startswith('/tournois/'):
             logger.error(f"Unrestricted URL for authenticated user: {current_url}")
             return self.get_response(request)

        # Définition des zones et permissions par rôle (pour les non-participants)
        role_permissions = {
            'organisateur': {
                'allowed_urls': [
                    '/tournois/',
                    '/tournois/creer/',
                    '/tournois/modifier/',
                    '/tournois/supprimer/',
                    '/tournois/gestion/',
                    '/matchs/',
                    '/statistiques/',
                    '/organisateurs/',  # Ajouter le chemin du tableau de bord organisateur
                ],
                'allowed_actions': [
                    'tournois:liste',
                    'tournois:detail',
                    'creer_tournoi',
                    'modifier_tournoi',
                    'supprimer_tournoi',
                    'gerer_tournoi',
                    'enregistrer_resultat',
                    'organisateurs:dashboard',  # Ajouter l'action du tableau de bord
                ],
                'message': "Cette section est réservée aux organisateurs de tournois."
            },
            'responsable': {
                'allowed_urls': [
                    '/equipes/',
                    '/equipes/gestion/',
                    '/equipes/modifier/',
                    '/equipes/creer/',
                    '/responsables/',
                    '/responsables/gestion_membres/',
                    '/responsables/ajouter_membre/',
                    '/responsables/modifier_membre/',
                    '/matchs/',  # Permettre l'accès aux matchs
                    '/matchs/nouveau/',  # Permettre la création de matchs
                    '/tournois/',  # Permettre l'accès aux tournois
                ],
                'allowed_actions': [
                     'equipes:liste_equipes',
                     'equipes:detail_equipe',
                    'creer_equipe',
                    'modifier_equipe',
                    'gerer_equipe',
                    'ajouter_membre',
                    'modifier_membre',
                    'supprimer_membre',
                    'matchs:liste',  # Permettre l'accès à la liste des matchs
                    'matchs:detail',  # Permettre l'accès aux détails d'un match
                    'matchs:creer_match',  # Permettre la création de matchs
                    'matchs:modifier',  # Permettre la modification de matchs
                    'matchs:supprimer',  # Permettre la suppression de matchs
                    'matchs:enregistrer_resultat', # Permettre d'enregistrer les résultats
                    'tournois:liste',  # Permettre l'accès à la liste des tournois
                    'tournois:detail',  # Permettre l'accès aux détails d'un tournoi
                ],
                'message': "Cette section est réservée aux responsables d'équipe."
            }
        }

        # Vérifier les permissions de l'utilisateur (non participant)
        user_type = getattr(request.user, 'type', None)
        logger.error(f"Checking permissions for user type: {user_type}, URL: {current_url}")
        
        # Si l'utilisateur a un type géré par ce middleware
        if user_type in role_permissions:
            # Obtenir les permissions pour le type d'utilisateur
            permissions = role_permissions.get(user_type, {})
            allowed_urls = permissions.get('allowed_urls', [])
            allowed_actions = permissions.get('allowed_actions', [])
            
            # Vérifier si l'URL actuelle est autorisée
            is_url_allowed = False
            
            # Vérifier les URLs autorisées par startswith
            for allowed_url in allowed_urls:
                if current_url.startswith(allowed_url):
                    is_url_allowed = True
                    logger.error(f"URL allowed by prefix: {current_url} (matched {allowed_url})")
                    break
            
            # Vérifier les actions autorisées par url_name (si disponible)
            if current_url_name is not None and current_url_name in allowed_actions:
                is_url_allowed = True
                logger.error(f"URL allowed by action: {current_url_name}")
            
            # Si l'URL n'est pas autorisée pour ce rôle, rediriger avec un message
            if not is_url_allowed:
                message = permissions.get('message', "Vous n'avez pas les permissions nécessaires pour accéder à cette section.")
                messages.error(request, message)
                logger.error(f"URL not allowed for user type {user_type}: {current_url}")
                
                # Redirection spécifique selon le type d'utilisateur
                if user_type == 'responsable':
                    logger.error(f"Redirecting responsable to tableau_bord")
                    return redirect('responsables:tableau_bord')
                elif user_type == 'organisateur':
                    logger.error(f"Redirecting organisateur to dashboard")
                    # Vérifier si nous sommes déjà sur la page de dashboard organisateur pour éviter une boucle
                    if current_url.startswith('/organisateurs/') and current_url != '/organisateurs/':
                        logger.error(f"Already in organisateurs section, redirecting to home")
                        return redirect('home')
                    return redirect('organisateurs:dashboard') # Redirection vers le tableau de bord des organisateurs
                else:
                    # Redirection par défaut si le type d'utilisateur n'est pas responsable ou organisateur (et non participant)
                    logger.error(f"Redirecting other user type to dashboard")
                    return redirect('dashboard') # Assurez-vous que cette URL est correcte et résolvable

            # Vérifications spécifiques pour certaines actions (pour les rôles gérés par ce middleware)
            if current_url_name == 'responsables:ajouter_membre':
                 if user_type != 'responsable':
                     messages.error(request, "Seuls les responsables d'équipe peuvent ajouter des membres.")
                     return redirect('dashboard')
                 # Vérification supplémentaire si le responsable a une équipe
                 if user_type == 'responsable':
                     try:
                         # Tenter de voir si l'utilisateur est responsable d'une équipe via le modèle
                         from equipes.models import Equipe # Importation locale pour éviter les dépendances circulaires si nécessaire
                         from responsables.models import Responsable
                         
                         # Récupérer d'abord l'objet Responsable
                         try:
                             responsable = Responsable.objects.get(user=request.user)
                             if not Equipe.objects.filter(responsable=responsable).exists():
                                 messages.error(request, "Vous devez d'abord créer une équipe pour ajouter des membres.")
                                 return redirect('equipes:creer_equipe')
                         except Responsable.DoesNotExist:
                             # Si le profil responsable n'existe pas encore
                             messages.error(request, "Vous n'avez pas encore de profil responsable. Veuillez créer une équipe.")
                             return redirect('equipes:creer_equipe')
                     except Exception as e:
                          logger.error(f"Error checking for responsable team: {e}")
                          messages.error(request, "Une erreur est survenue lors de la vérification de votre équipe.")
                          return redirect('dashboard') # Redirection sûre en cas d'erreur

            elif current_url_name == 'tournois:creer':
                 if user_type != 'organisateur':
                     messages.error(request, "Seuls les organisateurs peuvent créer des tournois.")
                     return redirect('dashboard')

        # Cas spécial pour /organisateurs/ - protection contre les boucles infinies
        if current_url == '/organisateurs/':
            logger.error("SPECIAL CASE: /organisateurs/ detected")
            
            # Vérifier si l'utilisateur est un organisateur
            if user_type != 'organisateur':
                logger.error(f"User {request.user.username} is not an organisateur (type: {user_type})")
                messages.error(request, "Cette section est réservée aux organisateurs de tournois.")
                return redirect('home')
                
            # Vérifier si l'utilisateur a déjà un profil Organisateur
            if not hasattr(request.user, 'organisateur'):
                try:
                    from organisateurs.models import Organisateur
                    logger.error(f"Creating organisateur profile for {request.user.username}")
                    organisateur, created = Organisateur.objects.get_or_create(user=request.user)
                    logger.error(f"Organisateur profile created: {created}")
                except Exception as e:
                    logger.error(f"ERROR creating organisateur profile: {str(e)}")
                    # Ne pas afficher de message d'erreur pour ne pas perturber l'utilisateur
                    return redirect('home')

        # Continuer avec la requête si l'accès est autorisé ou si le type d'utilisateur n'est pas géré ici
        logger.error(f"Access allowed, continuing with request for {current_url}")
        response = self.get_response(request)
        return response

class CSRFFixMiddleware:
    """
    Middleware qui s'assure que le jeton CSRF est correctement généré pour toutes les requêtes.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Générer le jeton CSRF pour toutes les requêtes
        from django.middleware.csrf import get_token
        get_token(request)
        
        # Continuer le traitement de la requête
        response = self.get_response(request)
        return response