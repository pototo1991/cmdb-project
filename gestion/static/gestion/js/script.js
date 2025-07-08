// Se ejecuta cuando todo el contenido del DOM ha sido cargado
document.addEventListener('DOMContentLoaded', (event) => {

    // --- Lógica para el Footer ---
    const dateElement = document.getElementById('footer-date');
    if (dateElement) {
        const currentYear = new Date().getFullYear();
        dateElement.textContent = `© ${currentYear} CMDB Systems. Todos los derechos reservados.`;
    }

    // --- Lógica para la página de incidencias (incidencias.html) ---
    const toggleButton = document.getElementById('toggle-filters-btn');
    const filterContainer = document.getElementById('filter-container');

    // Se comprueba que los elementos existen en la página actual
    if (toggleButton && filterContainer) {

        // El estado inicial ahora lo controla el HTML.
        // El script solo se encarga de la lógica del clic.
        toggleButton.addEventListener('click', function() {
            const isHidden = filterContainer.style.display === 'none';
            if (isHidden) {
                filterContainer.style.display = 'block';
                this.textContent = 'Ocultar';
            } else {
                filterContainer.style.display = 'none';
                this.textContent = 'Mostrar Filtros';
            }
        });
    }

});