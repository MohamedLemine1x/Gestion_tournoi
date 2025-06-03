import os
import ssl
from pathlib import Path
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-votre-clé-secrète')
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition 
INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.flatpages',
    
    # Third-party apps
    'widget_tweaks',
    'django_bootstrap5',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Project apps
    'accounts',
    'tournois',
    'equipes',
    'matchs',
    'statistiques',
    'responsables',
    'organisateurs',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # This needs to run before any middleware using request.user
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware after Django's built-in ones
    'tournoi_foot.middleware.CSRFFixMiddleware',
    'tournoi_foot.middleware.RedirectionLoopProtectionMiddleware',
    'tournoi_foot.middleware.ParticipantAccessMiddleware',
    'tournoi_foot.middleware.RoleBasedAccessMiddleware',
]

# Configuration pour CSRF
CSRF_COOKIE_SECURE = False  # Mettre à True en production avec HTTPS
CSRF_COOKIE_HTTPONLY = False  # Permettre l'accès JavaScript au cookie CSRF
CSRF_USE_SESSIONS = False  # Stockage du token dans un cookie plutôt que dans la session
CSRF_COOKIE_AGE = 86400  # 24 heures en secondes

ROOT_URLCONF = 'tournoi_foot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.csrf',
            ],
        },
    },
]

WSGI_APPLICATION = 'tournoi_foot.wsgi.application'

# Paramètres de session
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 86400  # 24 heures, en secondes

# Définition du modèle utilisateur personnalisé
AUTH_USER_MODEL = 'accounts.CustomUser'

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gestion_tournoi',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'STRICT_TRANS_TABLES',
            'charset': 'utf8mb4',
            'use_unicode': True,
            'init_command': (
                'SET innodb_strict_mode=0; '
                'SET character_set_connection=utf8mb4; '
                'SET collation_connection=utf8mb4_unicode_ci; '
                'SET default_storage_engine=INNODB;'
            ),
        }
    }
}

# Authentication backend
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Configuration du site pour les URLs dans les emails
SITE_ID = 1
SITE_DOMAIN = 'localhost:8000'
SITE_NAME = 'TournoiPRO'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login/Logout
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'accounts:login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static and media files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Configuration supplémentaire pour les fichiers statiques
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Messages
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Durée de validité des liens de réinitialisation du mot de passe (24 heures)
PASSWORD_RESET_TIMEOUT = 86400

# Email Configuration
# Configuration email - Facilement basculer entre développement et production
USE_CONSOLE_EMAIL = True  # Mettre à False pour utiliser SMTP

if USE_CONSOLE_EMAIL:
    # Pour le développement - Affiche les emails dans la console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Pour la production - Envoie des emails réels
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'votre_email@gmail.com')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'votre_mot_de_passe_app')
    EMAIL_TIMEOUT = 30  # timeout en secondes

DEFAULT_FROM_EMAIL = 'noreply@tournoipro.com'
SERVER_EMAIL = 'noreply@tournoipro.com'

# Configuration pour la réinitialisation du mot de passe
PASSWORD_RESET_TIMEOUT = 86400  # 24 heures en secondes

# Configuration du logging pour le débogage
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
            'formatter': 'verbose',
        },
        'mail_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'mail_debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.mail': {
            'handlers': ['console', 'mail_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'organisateurs': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'responsables': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'tournois': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'equipes': {
            'handlers': ['console', 'file', 'mail_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


SITE_ID = 1