// Se ejecuta cuando todo el contenido del DOM ha sido cargado
// Se ejecuta cuando todo el contenido del DOM ha sido cargado
document.addEventListener('DOMContentLoaded', (event) => {

    // --- Lógica para el Footer ---
    const dateElement = document.getElementById('footer-date');
    if (dateElement) {
        const currentYear = new Date().getFullYear();
        dateElement.textContent = `© ${currentYear} CMDB Systems. Todos los derechos reservados.`;
    }

    // La lógica de los filtros se ha movido a la plantilla 'incidencia.html'
    // para evitar conflictos y mantener el código específico en su lugar.

});