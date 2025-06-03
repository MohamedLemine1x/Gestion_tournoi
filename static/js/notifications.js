/**
 * notifications.js - Gestion avancée des notifications côté client
 * Version 2.0 - Amélioration UX et fonctionnalités
 */

class NotificationManager {
    constructor(options = {}) {
        this.options = Object.assign({
            refreshInterval: 60000, // Increased from 20s to 60s to reduce server requests
            notificationBadgeSelector: '.notification-badge',
            notificationBellSelector: '#notification-bell',
            notificationListSelector: '#navbar-notification-list',
            notificationIndicatorSelector: '#notification-indicator',
            initialDelay: 3000, // Increased to 3 seconds for initial load
            maxNotifications: 100,
            apiUrl: '/notifications/api/get-notifications/',
            filterSelector: '.notification-filter',
            emptyNotificationId: 'empty-notification-message',
            notificationDropdownSelector: '.notification-dropdown',
            soundEnabled: true,
            animationEnabled: true,
            // Add cache expiry setting
            cacheExpiryTime: 30000 // 30 seconds
        }, options);

        // Éléments DOM
        this.notificationBadge = document.querySelector(this.options.notificationBadgeSelector);
        this.notificationBell = document.querySelector(this.options.notificationBellSelector);
        this.notificationList = document.querySelector(this.options.notificationListSelector);
        this.notificationIndicator = document.querySelector(this.options.notificationIndicatorSelector);
        this.notificationDropdown = document.querySelector(this.options.notificationDropdownSelector);
        
        // État des notifications
        this.currentFilter = 'all';
        this.lastNotificationCount = 0;
        this.notificationSound = null; // Lazy load sound
        this.notificationCache = {
            data: null,
            timestamp: 0
        };
        
        // Initialisation
        this.init();
    }
    
    init() {
        if (!this.notificationBell && !this.notificationIndicator) return;
        
        // Setup bell animation with reduced frequency
        if (this.options.animationEnabled) {
            this.setupBellAnimation();
        }
        
        // Initial load after delay
        setTimeout(() => this.fetchNotifications(), this.options.initialDelay);
        
        // Periodic refresh with increased interval
        this.refreshInterval = setInterval(() => this.fetchNotifications(), this.options.refreshInterval);
        
        // Initialize event listeners
        this.setupEventListeners();
        
        // Create category filters only when dropdown is opened
        if (this.notificationDropdown) {
            this.notificationDropdown.addEventListener('shown.bs.dropdown', () => {
                // Only create filters if they don't already exist
                if (!this.notificationDropdown.querySelector('.notification-filters')) {
                    this.createCategoryFilters();
                }
            });
        }
        
        // Set global initialization flag
        window.notificationManagerInitialized = true;
        console.log('NotificationManager initialized');
    }
    
    createCategoryFilters() {
        const filterContainer = document.createElement('div');
        filterContainer.className = 'notification-filters d-flex flex-wrap p-2 border-bottom';
        
        const categories = [
            {id: 'all', name: 'Toutes', icon: 'fas fa-list', color: 'primary'},
            {id: 'info', name: 'Info', icon: 'fas fa-info-circle', color: 'info'},
            {id: 'match_amical', name: 'Match', icon: 'fas fa-futbol', color: 'success'},
            {id: 'tournoi', name: 'Tournoi', icon: 'fas fa-trophy', color: 'danger'},
            {id: 'equipe', name: 'Équipe', icon: 'fas fa-users', color: 'warning'},
            {id: 'resultat', name: 'Résultat', icon: 'fas fa-clipboard-list', color: 'secondary'}
        ];
        
        categories.forEach(category => {
            const filter = document.createElement('button');
            filter.type = 'button';
            filter.className = `btn btn-sm me-1 mb-1 btn-${this.currentFilter === category.id ? category.color : 'outline-' + category.color} notification-filter`;
            filter.dataset.category = category.id;
            filter.innerHTML = `<i class="${category.icon} me-1"></i>${category.name}`;
            filter.addEventListener('click', () => this.filterNotifications(category.id));
            
            filterContainer.appendChild(filter);
        });
        
        if (this.notificationDropdown) {
            const header = this.notificationDropdown.querySelector('.notification-header');
            if (header && header.nextElementSibling) {
                this.notificationDropdown.insertBefore(filterContainer, header.nextElementSibling);
            }
        }
    }
    
    initializeTooltips() {
        // Only initialize tooltips in the notification area to avoid performance hit
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip && this.notificationDropdown) {
            const tooltips = this.notificationDropdown.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach(tooltip => {
                new bootstrap.Tooltip(tooltip);
            });
        }
    }
    
    setupBellAnimation() {
        // Reduced animation frequency to 60 seconds instead of 30
        setInterval(() => {
            if (this.notificationBell && this.lastNotificationCount > 0) {
                this.notificationBell.classList.add('bell-animation');
                setTimeout(() => {
                    this.notificationBell.classList.remove('bell-animation');
                }, 1000);
            }
        }, 60000);
    }
    
    setupEventListeners() {
        // Handle marking notifications as read
        const markAllReadForm = document.getElementById('mark-all-read-form-navbar');
        if (markAllReadForm) {
            markAllReadForm.addEventListener('submit', (e) => this.handleMarkAllRead(e, markAllReadForm));
        }
        
        // Listener for floating indicator
        if (this.notificationIndicator) {
            this.notificationIndicator.addEventListener('click', () => {
                if (this.notificationBell) {
                    this.notificationBell.click();
                } else {
                    window.location.href = '/notifications/';
                }
            });
        }
        
        // Refresh notifications when dropdown opens
        if (typeof bootstrap !== 'undefined' && this.notificationDropdown) {
            this.notificationDropdown.addEventListener('shown.bs.dropdown', () => {
                this.fetchNotifications(true); // Force refresh when dropdown opens
            });
        }
        
        // Mark notification as read on click
        document.addEventListener('click', (e) => {
            const notificationItem = e.target.closest('.notification-item');
            if (notificationItem && notificationItem.classList.contains('unread')) {
                const notificationId = notificationItem.dataset.id;
                if (notificationId) {
                    this.markAsRead(notificationId);
                }
            }
        });
    }
    
    filterNotifications(category) {
        this.currentFilter = category;
        
        // Update filter buttons
        const filters = document.querySelectorAll(this.options.filterSelector);
        filters.forEach(filter => {
            const cat = filter.dataset.category;
            const color = this.getCategoryColor(cat);
            
            if (cat === category) {
                filter.className = filter.className.replace(/btn-outline-\w+/, `btn-${color}`);
            } else {
                filter.className = filter.className.replace(/btn-\w+/, `btn-outline-${color}`);
            }
        });
        
        // Refresh notifications with filter
        this.fetchNotifications(true); // Force refresh when filter changes
    }
    
    getCategoryColor(category) {
        switch (category) {
            case 'info': return 'info';
            case 'match_amical': return 'success';
            case 'tournoi': return 'danger';
            case 'equipe': return 'warning';
            case 'resultat': return 'secondary';
            default: return 'primary';
        }
    }
    
    getCategoryIcon(category) {
        switch (category) {
            case 'info': return 'fas fa-info-circle';
            case 'match_amical': return 'fas fa-futbol';
            case 'tournoi': return 'fas fa-trophy';
            case 'equipe': return 'fas fa-users';
            case 'resultat': return 'fas fa-clipboard-list';
            default: return 'fas fa-bell';
        }
    }
    
    handleMarkAllRead(e, form) {
        e.preventDefault();
        
        const url = form.action;
        const formData = new FormData(form);
        
        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear notification cache
                this.notificationCache.data = null;
                this.fetchNotifications(true);
            }
        })
        .catch(error => console.error('Error marking all as read:', error));
    }
    
    markAsRead(notificationId) {
        const url = `/notifications/marquer-lu/${notificationId}/`;
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notification = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
                if (notification) {
                    notification.classList.remove('unread');
                    this.lastNotificationCount--;
                    this.updateBadge(this.lastNotificationCount);
                }
            }
        })
        .catch(error => console.error('Error marking notification as read:', error));
    }
    
    fetchNotifications(forceRefresh = false) {
        // Check if we can use cached data
        const now = Date.now();
        if (!forceRefresh && 
            this.notificationCache.data && 
            (now - this.notificationCache.timestamp < this.options.cacheExpiryTime)) {
            this.updateNotifications(this.notificationCache.data);
            return;
        }
        
        const url = `${this.options.apiUrl}?filter=${this.currentFilter}&_=${now}`;
        
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Cache the response
            this.notificationCache.data = data;
            this.notificationCache.timestamp = now;
            
            this.updateNotifications(data);
        })
        .catch(error => console.error('Error fetching notifications:', error));
    }
    
    updateNotifications(data) {
        // Update the badge count
        this.updateBadge(data.count);
        
        // Update notification list if it exists
        if (this.notificationList) {
            this.updateNotificationList(data.notifications);
        }
        
        // Play sound if new notifications arrived
        if (data.count > this.lastNotificationCount && this.options.soundEnabled) {
            this.playNotificationSound();
        }
        
        // Update last count
        this.lastNotificationCount = data.count;
    }
    
    updateBadge(count) {
        if (this.notificationBadge) {
            this.notificationBadge.textContent = count;
            
            if (count > 0) {
                this.notificationBadge.style.display = 'inline-block';
            } else {
                this.notificationBadge.style.display = 'none';
            }
        }
        
        // Update notification indicator if it exists
        if (this.notificationIndicator) {
            if (count > 0) {
                this.notificationIndicator.classList.remove('d-none');
                this.notificationIndicator.classList.add('show');
                
                const countElement = this.notificationIndicator.querySelector('.count');
                if (countElement) {
                    countElement.textContent = count;
                }
            } else {
                this.notificationIndicator.classList.remove('show');
                setTimeout(() => {
                    if (this.notificationIndicator && 
                        !this.notificationIndicator.classList.contains('show')) {
                        this.notificationIndicator.classList.add('d-none');
                    }
                }, 300);
            }
        }
    }
    
    updateNotificationList(notifications) {
        if (!this.notificationList) return;
        
        // Clear existing notifications
        this.notificationList.innerHTML = '';
        
        if (!notifications || notifications.length === 0) {
            // Empty state
            const emptyMessage = document.createElement('div');
            emptyMessage.id = this.options.emptyNotificationId;
            emptyMessage.className = 'p-4 text-center text-muted';
            emptyMessage.innerHTML = '<i class="far fa-bell-slash mb-3 d-block" style="font-size: 2rem;"></i>Aucune notification.';
            
            this.notificationList.appendChild(emptyMessage);
            return;
        }
        
        // Create a document fragment for better performance
        const fragment = document.createDocumentFragment();
        
        notifications.forEach((notification, index) => {
            const notificationItem = document.createElement('div');
            notificationItem.className = 'notification-item unread d-flex p-3 border-bottom';
            notificationItem.dataset.id = notification.id;
            
            // Only add data-aos for the first 5 items to reduce rendering load
            if (index < 5) {
                notificationItem.setAttribute('data-aos', 'fade-up');
                notificationItem.setAttribute('data-aos-delay', (index * 50).toString());
            }
            
            const categoryIcon = this.getCategoryIcon(notification.type);
            const categoryColor = this.getCategoryColor(notification.type);
            
            notificationItem.innerHTML = `
                <div class="me-3">
                    <div class="notification-icon bg-${categoryColor}-subtle rounded-circle p-2">
                        <i class="${categoryIcon} text-${categoryColor}"></i>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <h6 class="notification-title mb-1">${notification.titre}</h6>
                    <p class="notification-message mb-1">${notification.message}</p>
                    <div class="notification-time text-muted small">${notification.date}</div>
                </div>
                <div class="ms-2">
                    <button type="button" class="mark-read-btn btn btn-sm btn-link p-0" 
                        data-notification-id="${notification.id}" 
                        data-bs-toggle="tooltip" 
                        data-bs-placement="left" 
                        title="Marquer comme lu">
                        <i class="far fa-check-circle"></i>
                    </button>
                </div>
            `;
            
            // Add click event to redirect to notification link
            notificationItem.addEventListener('click', (e) => {
                // Don't redirect if clicking on the mark as read button
                if (!e.target.closest('.mark-read-btn')) {
                    window.location.href = notification.lien;
                }
            });
            
            fragment.appendChild(notificationItem);
        });
        
        this.notificationList.appendChild(fragment);
        
        // Initialize tooltips for new items
        this.initializeTooltips();
    }
    
    playNotificationSound() {
        // Lazy load the sound only when needed
        if (!this.notificationSound) {
            this.notificationSound = new Audio('/static/sounds/notification.mp3');
        }
        
        // Play only if tab is not active
        if (document.hidden && this.options.soundEnabled) {
            try {
                this.notificationSound.play().catch(e => {
                    // Ignore autoplay errors
                    console.log('Sound could not be played automatically');
                });
            } catch (e) {
                // Ignore errors
            }
        }
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
            
        return cookieValue ? cookieValue.split('=')[1] : '';
    }
    
    getCategoryName(category) {
        switch (category) {
            case 'info': return 'Information';
            case 'match_amical': return 'Match amical';
            case 'tournoi': return 'Tournoi';
            case 'equipe': return 'Équipe';
            case 'resultat': return 'Résultat';
            default: return 'Notification';
        }
    }
    
    markGroupAsRead(type) {
        const url = '/notifications/marquer-groupe-lu/';
        
        const formData = new FormData();
        formData.append('type', type);
        formData.append('csrfmiddlewaretoken', this.getCSRFToken());
        
        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear cache and force refresh
                this.notificationCache.data = null;
                this.fetchNotifications(true);
            }
        })
        .catch(error => console.error('Error marking group as read:', error));
    }
}

// Initialisation quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    // Créer l'instance du gestionnaire de notifications
    window.notificationManager = new NotificationManager();
    
    // Ajouter un gestionnaire d'événement pour le scroll pour montrer/cacher l'indicateur flottant
    window.addEventListener('scroll', () => {
        const notificationManager = window.notificationManager;
        if (!notificationManager || !notificationManager.notificationIndicator) return;
        
        if (window.scrollY > 100 && notificationManager.lastNotificationCount > 0) {
            notificationManager.notificationIndicator.classList.remove('d-none');
            notificationManager.notificationIndicator.classList.add('show');
        } else {
            notificationManager.notificationIndicator.classList.remove('show');
            setTimeout(() => {
                if (notificationManager.notificationIndicator && 
                    !notificationManager.notificationIndicator.classList.contains('show')) {
                    notificationManager.notificationIndicator.classList.add('d-none');
                }
            }, 300);
        }
    });
}); 