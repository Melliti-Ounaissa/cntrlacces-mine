// static/js/main.js
// Fonctions utilitaires + UI

// ========== UI (sidebar + alerts) ==========
document.addEventListener("DOMContentLoaded", () => {
  // Toggle sidebar (mobile)
  const btn = document.getElementById("btnSidebar");
  const sidebar = document.getElementById("sidebar");

  if (btn && sidebar) {
    btn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Fermer les alertes (si pas de onclick dans HTML)
  document.querySelectorAll(".alert-close").forEach((b) => {
    b.addEventListener("click", () => {
      b.closest(".alert")?.remove();
    });
  });
});

// ========== Utils ==========

// Confirmation de suppression
function confirmDelete(message) {
  return confirm(message || "Êtes-vous sûr de vouloir supprimer cet élément ?");
}

// Formatage de date
function formatDate(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("fr-FR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Vérification RBAC côté client (optionnel)
function checkAccess(action) {
  // À implémenter si besoin de vérifications AJAX
  return true;
}
