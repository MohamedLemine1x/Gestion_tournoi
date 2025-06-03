# equipes/admin.py (version simple)
from django.contrib import admin
from .models import Equipe, MembreEquipe

@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'responsable', 'date_creation']
    list_filter = ['date_creation']
    search_fields = ['nom', 'responsable__username']
    readonly_fields = ['date_creation']

@admin.register(MembreEquipe)
class MembreEquipeAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'equipe', 'position', 'date_ajout']
    list_filter = ['position', 'date_ajout', 'equipe']
    search_fields = ['utilisateur__username', 'equipe__nom']
    readonly_fields = ['date_ajout']