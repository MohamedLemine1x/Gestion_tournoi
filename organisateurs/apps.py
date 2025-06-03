from django.apps import AppConfig


class OrganisateursConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'organisateurs'
    
    def ready(self):
        """Connect signals when the app is ready."""
        import organisateurs.models  # noqa
