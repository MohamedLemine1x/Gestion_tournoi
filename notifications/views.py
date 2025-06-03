from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.timesince import timesince
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .models import Notification
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def liste_notifications(request):
    """
    Affiche toutes les notifications de l'utilisateur connecté.
    """
    notifications = Notification.objects.filter(destinataire=request.user)
    
    # Pagination - 15 notifications par page
    paginator = Paginator(notifications, 15)
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)
    
    context = {
        'notifications': notifications_page,
        'page_title': 'Mes notifications',
        'breadcrumbs': [
            {'name': 'Accueil', 'url': 'home'},
            {'name': 'Notifications', 'url': None, 'active': True},
        ]
    }
    
    return render(request, 'notifications/liste_notifications.html', context)

@login_required
@require_POST
def marquer_notification_lue(request, notification_id):
    """
    Marque une notification spécifique comme lue.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id, destinataire=request.user)
        notification.marquer_comme_lu()
        
        # Clear cache for this user's notifications
        cache_key = f'user_notifications_{request.user.id}'
        cache.delete(cache_key)
        
        # Si la requête est AJAX, renvoyer une réponse JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        # Rediriger vers le lien de la notification si présent
        if notification.lien:
            return redirect(notification.lien)
        
        # Sinon, retourner à la liste des notifications
        return redirect('notifications:liste')
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return redirect('notifications:liste')

@login_required
@require_POST
def marquer_toutes_lues(request):
    """
    Marque toutes les notifications de l'utilisateur connecté comme lues.
    """
    try:
        notifications = Notification.objects.filter(destinataire=request.user, lu=False)
        count = notifications.count()
        notifications.update(lu=True)
        
        # Clear cache for this user's notifications
        cache_key = f'user_notifications_{request.user.id}'
        cache.delete(cache_key)
        
        # Si la requête est AJAX, renvoyer une réponse JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': count})
        
        return redirect('notifications:liste')
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return redirect('notifications:liste')

@login_required
@require_POST
def supprimer_notification(request, notification_id):
    """
    Supprime une notification spécifique.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id, destinataire=request.user)
        notification.delete()
        
        # Clear cache for this user's notifications
        cache_key = f'user_notifications_{request.user.id}'
        cache.delete(cache_key)
        
        # Si la requête est AJAX, renvoyer une réponse JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('notifications:liste')
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return redirect('notifications:liste')

@login_required
@require_GET
def get_notifications_ajax(request):
    """
    Renvoie les notifications non lues de l'utilisateur sous format JSON
    pour la mise à jour dynamique du menu de notifications.
    """
    try:
        # Récupérer le filtre de catégorie demandé
        category_filter = request.GET.get('filter', 'all')
        
        # Force refresh if _=timestamp is in the URL
        force_refresh = request.GET.get('_') is not None
        
        # Check cache first for unfiltered data
        cache_key = f'user_notifications_{request.user.id}'
        cached_data = None if force_refresh else cache.get(cache_key)
        
        if not cached_data:
            # Get all unread notifications in a single query with select_related if needed
            unread_notifications = Notification.objects.filter(
                destinataire=request.user,
                lu=False
            ).order_by('-date_creation')
            
            # Process all notifications
            all_notifications_data = []
            for notif in unread_notifications:
                time_since = timesince(notif.date_creation).split(',')[0]
                
                all_notifications_data.append({
                    'id': notif.id,
                    'titre': notif.titre,
                    'message': notif.message,
                    'lien': notif.lien if notif.lien else reverse('notifications:liste'),
                    'date': f"Il y a {time_since}",
                    'type': notif.type_notification
                })
            
            # Count notifications by category
            category_counts = {}
            for category_code, _ in Notification.TYPES_NOTIFICATION:
                category_counts[category_code] = sum(1 for n in unread_notifications if n.type_notification == category_code)
            
            # Cache the complete result for 30 seconds
            cached_data = {
                'all_notifications': all_notifications_data,
                'count': len(all_notifications_data),
                'category_counts': category_counts
            }
            cache.set(cache_key, cached_data, 30)  # Cache for 30 seconds
        
        # Now filter the data based on category_filter
        if category_filter != 'all':
            notifications_data = [n for n in cached_data['all_notifications'] 
                                if n['type'] == category_filter]
        else:
            notifications_data = cached_data['all_notifications']
        
        # Return the appropriate data
        data = {
            'notifications': notifications_data,
            'count': cached_data['count'],
            'category_counts': cached_data['category_counts'],
            'current_filter': category_filter
        }
        
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return JsonResponse({
            'notifications': [],
            'count': 0,
            'category_counts': {},
            'current_filter': category_filter,
            'error': str(e)
        })

@login_required
def notification_detail(request, notification_id):
    """
    Affiche le détail d'une notification et la marque comme lue.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id, destinataire=request.user)
        
        # Marquer comme lue si ce n'est pas déjà le cas
        if not notification.lu:
            notification.marquer_comme_lu()
            
            # Clear cache for this user's notifications
            cache_key = f'user_notifications_{request.user.id}'
            cache.delete(cache_key)
        
        context = {
            'notification': notification,
            'page_title': f'Détail notification: {notification.titre}',
            'breadcrumbs': [
                {'name': 'Accueil', 'url': 'home'},
                {'name': 'Notifications', 'url': 'notifications:liste'},
                {'name': notification.titre[:20] + '...', 'url': None, 'active': True},
            ]
        }
        
        return render(request, 'notifications/detail_notification.html', context)
    except Exception as e:
        logger.error(f"Error viewing notification detail: {str(e)}")
        return render(request, 'error.html', {
            'title': 'Erreur de notification',
            'message': 'Impossible d\'afficher cette notification.',
            'details': str(e)
        })

@login_required
@require_POST
def marquer_groupe_lu(request):
    """
    Marque toutes les notifications d'un type spécifique comme lues.
    """
    try:
        notification_ids = []
        try:
            notification_ids = json.loads(request.POST.get('notification_ids', '[]'))
        except json.JSONDecodeError:
            notification_ids = []
        
        type_notification = request.POST.get('type', '')
        
        # Si une liste d'IDs est fournie, marquer ces notifications comme lues
        if notification_ids:
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                destinataire=request.user,
                lu=False
            )
        # Sinon, marquer toutes les notifications du type comme lues
        elif type_notification and type_notification in dict(Notification.TYPES_NOTIFICATION).keys():
            notifications = Notification.objects.filter(
                destinataire=request.user,
                type_notification=type_notification,
                lu=False
            )
        else:
            return JsonResponse({'success': False, 'message': 'Type de notification invalide'})
        
        count = notifications.count()
        notifications.update(lu=True)
        
        # Clear cache for this user's notifications
        cache_key = f'user_notifications_{request.user.id}'
        cache.delete(cache_key)
        
        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Error marking notification group as read: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
