// gestion\static\gestion\js\carga_masiva.js

$(document).ready(function() {
    // ---===================================================---
    // --- JAVASCRIPT PARA TODAS LAS PÁGINAS DE CARGA MASIVA ---
    // ---===================================================---

    // Esta sección se aplica a cualquier página que tenga un
    // input de tipo 'file' con el id 'csv_file'.

    const fileInput = $('#csv_file');

    // Comprobamos si el input de archivo existe en la página actual
    if (fileInput.length > 0) {

        // 1. Funcionalidad para mostrar el nombre del archivo seleccionado
        // ---------------------------------------------------------------

        // Creamos un <span> para mostrar el nombre, justo después del botón de input
        fileInput.after('<span id="file-name-display" class="file-name">Ningún archivo seleccionado</span>');
        const fileNameDisplay = $('#file-name-display');

        // Cuando el usuario selecciona un archivo, actualizamos el texto del <span>
        fileInput.on('change', function() {
            if (this.files && this.files.length > 0) {
                // Mostramos el nombre del primer archivo seleccionado
                fileNameDisplay.text(this.files[0].name);
            } else {
                // Si el usuario cancela, volvemos al texto original
                fileNameDisplay.text('Ningún archivo seleccionado');
            }
        });


        // 2. Funcionalidad para mostrar el spinner al cargar el archivo
        // -------------------------------------------------------------

        const form = fileInput.closest('form');
        if (form.length > 0) {
            form.on('submit', function() {
                // Buscamos si el botón de submit tiene la clase 'link-con-spinner'
                const submitButton = $(this).find('button[type="submit"]');
                if (submitButton.hasClass('link-con-spinner')) {
                    // Asumiendo que tu 'base.html' tiene un spinner con id 'loading-spinner', lo mostramos
                    $('#loading-spinner').css('display', 'flex');
                }
            });
        }
    }
});