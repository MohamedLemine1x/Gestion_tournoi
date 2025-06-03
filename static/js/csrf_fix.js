// Script pour corriger les problèmes liés aux tokens CSRF

// Fonction pour obtenir le token CSRF à partir des cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Le nom du cookie CSRF commence par le nom + '='
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fonction pour ajouter le token CSRF à tous les formulaires
function addCSRFTokenToForms() {
    const csrftoken = getCookie('csrftoken');
    if (!csrftoken) return; // Si pas de token, on ne fait rien
    
    // Ajouter le token à tous les formulaires qui n'en ont pas déjà
    document.querySelectorAll('form').forEach(form => {
        // Si le formulaire n'a pas de méthode ou si c'est GET, on ne fait rien
        if (!form.method || form.method.toLowerCase() === 'get') return;
        
        // Si le formulaire n'a pas déjà un champ CSRF
        if (!form.querySelector('input[name="csrfmiddlewaretoken"]')) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrfmiddlewaretoken';
            input.value = csrftoken;
            form.appendChild(input);
            console.log('CSRF token ajouté au formulaire:', form);
        }
    });
}

// Fonction pour configurer les requêtes AJAX avec le token CSRF
function setupAjaxCSRF() {
    const csrftoken = getCookie('csrftoken');
    if (!csrftoken) return; // Si pas de token, on ne fait rien
    
    // Pour jQuery (si disponible)
    if (typeof $ !== 'undefined') {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!this.crossDomain && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                }
            }
        });
        console.log('CSRF configuré pour jQuery AJAX');
    }
    
    // Pour Fetch API (méthode native)
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        options = options || {};
        options.headers = options.headers || {};
        
        // Ajouter le token CSRF pour les requêtes non-GET
        if (options.method && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method)) {
            options.headers['X-CSRFToken'] = csrftoken;
        }
        
        return originalFetch(url, options);
    };
    console.log('CSRF configuré pour Fetch API');
}

// Exécuter ces fonctions lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initialisation de la protection CSRF...');
    addCSRFTokenToForms();
    setupAjaxCSRF();
    
    // Réparer également les formulaires qui seraient ajoutés dynamiquement
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                // Vérifier uniquement si de nouveaux nœuds ont été ajoutés
                addCSRFTokenToForms();
            }
        });
    });
    
    // Observer les changements dans le corps du document
    observer.observe(document.body, { childList: true, subtree: true });
    
    console.log('Protection CSRF initialisée.');
});

// Exécuter immédiatement si le DOM est déjà chargé
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    addCSRFTokenToForms();
    setupAjaxCSRF();
} 