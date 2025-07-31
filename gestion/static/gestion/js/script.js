// Se ejecuta cuando todo el contenido del DOM ha sido cargado
document.addEventListener('DOMContentLoaded', (event) => {

    // --- Lógica para el Spinner de Carga ---
    const spinner = document.getElementById('loading-spinner');

    if (spinner) {
        // 1. Lógica para Formularios
        const formsConSpinner = document.querySelectorAll('.form-con-spinner');
        formsConSpinner.forEach(form => {
            form.addEventListener('submit', function() {
                spinner.style.display = 'flex';
            });
        });

        // 2. Lógica para Enlaces de NAVEGACIÓN (páginas lentas)
        // Busca enlaces que tengan 'link-con-spinner' pero NO 'download-link'
        const navLinks = document.querySelectorAll('.link-con-spinner:not(.download-link)');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                spinner.style.display = 'flex';
            });
        });

        // 3. Lógica para Enlaces de DESCARGA
        const downloadLinks = document.querySelectorAll('.download-link');
        downloadLinks.forEach(link => {
            link.addEventListener('click', function() {
                spinner.style.display = 'flex';

                // Inicia un intervalo para verificar la cookie cada 500ms
                const cookieCheckInterval = setInterval(function() {
                    // Busca la cookie 'descargaFinalizada=true'
                    if (document.cookie.split(';').some((item) => item.trim().startsWith('descargaFinalizada='))) {

                        // Si la encuentra:
                        // 1. Detiene la verificación
                        clearInterval(cookieCheckInterval);

                        // 2. Oculta el spinner
                        spinner.style.display = 'none';

                        // 3. Limpia la cookie para la próxima vez
                        document.cookie = "descargaFinalizada=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
                    }
                }, 500);
            });
        });
    }

    // --- Lógica para el Footer ---
    const dateElement = document.getElementById('footer-date');
    if (dateElement) {
        const currentYear = new Date().getFullYear();
        dateElement.textContent = `© ${currentYear} CMDB Systems. Todos los derechos reservados.`;
    }
});