from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'destinataire', 'type_notification', 'date_creation', 'lu')
    list_filter = ('lu', 'type_notification', 'date_creation')
    search_fields = ('titre', 'message', 'destinataire__username', 'destinataire__email')
    date_hierarchy = 'date_creation'
    ordering = ('-date_creation',)
