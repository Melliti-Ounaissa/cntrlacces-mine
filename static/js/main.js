// static/js/main.js
// Fonctions utilitaires

// Confirmation de suppression
function confirmDelete(message) {
    return confirm(message || "Êtes-vous sûr de vouloir supprimer cet élément ?");
}

// Formatage de date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Vérification RBAC côté client (optionnel)
function checkAccess(action) {
    // À implémenter si besoin de vérifications AJAX
    return true;
}