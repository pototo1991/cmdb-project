// Se ejecuta cuando todo el contenido del DOM ha sido cargado
document.addEventListener('DOMContentLoaded', (event) => {

    // --- Lógica para el Footer (reutilizable en todas las páginas) ---
    const dateElement = document.getElementById('footer-date');
    if (dateElement) {
        const currentYear = new Date().getFullYear();
        dateElement.textContent = `© ${currentYear} CMDB Systems. Todos los derechos reservados.`;
    }

    // --- Lógica para la página principal (main.html) ---
    const btnIncidencias = document.getElementById('btn-incidencias');
    const btnActivos = document.getElementById('btn-activos');

    if (btnIncidencias) {
        btnIncidencias.addEventListener('click', () => {
            alert('Navegando a la gestión de incidencias...');
            // Lógica para redirigir, por ejemplo:
            // window.location.href = '/incidencias/';
        });
    }

    if (btnActivos) {
        btnActivos.addEventListener('click', () => {
            alert('Mostrando el listado de activos...');
            // Lógica para redirigir, por ejemplo:
            // window.location.href = '/activos/';
        });
    }

    // --- Lógica para la página de incidencias (incidencias.html) ---
    const toggleButton = document.getElementById('toggle-filters-btn');
    const filterContainer = document.getElementById('filter-container');

    // Se comprueba que los elementos existen antes de añadir el evento
    if (toggleButton && filterContainer) {
        toggleButton.addEventListener('click', function() {
            // Se alterna la visibilidad del contenedor de filtros
            const isHidden = filterContainer.style.display === 'none';
            if (isHidden) {
                filterContainer.style.display = 'block';
                toggleButton.textContent = 'Ocultar';
            } else {
                filterContainer.style.display = 'none';
                toggleButton.textContent = 'Mostrar Filtros';
            }
        });
    }

});