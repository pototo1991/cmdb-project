// gestion\static\gestion\js\aplicaciones.js

$(document).ready(function() {
    // --- Lógica para los botones de filtro ---
    const toggleBtn = document.getElementById('toggle-filters-btn');
    const filterContainer = document.getElementById('filter-container');

    // Mostrar filtros si hay alguno aplicado al cargar la página
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.toString() !== '') {
        let hasFilter = false;
        for (const value of urlParams.values()) {
            if (value) {
                hasFilter = true;
                break;
            }
        }
        if (hasFilter) {
            filterContainer.style.display = 'block';
            toggleBtn.textContent = 'Ocultar Filtros';
        }
    }

    toggleBtn.addEventListener('click', function() {
        const isHidden = filterContainer.style.display === 'none';
        filterContainer.style.display = isHidden ? 'block' : 'none';
        this.textContent = isHidden ? 'Ocultar Filtros' : 'Mostrar Filtros';
    });

    // Lógica para el botón de limpiar filtros
    document.getElementById('limpiar-filtros-btn').addEventListener('click', function() {
        window.location.href = window.location.pathname;
    });

    // --- Inicialización de DataTables ---
    $('#tabla-aplicaciones').DataTable({
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de un total de _MAX_ registros)",
            "search": "Buscar:",
            "paginate": { "first": "Primero", "last": "Último", "next": "Siguiente", "previous": "Anterior" }
        },
        "pageLength": 25,
        "order": [
            [3, "asc"]
        ], // Ordenar por nombre de aplicación
        // =======================================================
        //     SECCIÓN AÑADIDA PARA AJUSTAR LAS COLUMNAS
        // =======================================================
        "columnDefs": [
            { "width": "5%", "targets": [0, 1], "orderable": false }, // Eliminar y Editar (no ordenables)
            { "width": "9%", "targets": 2 }, // Código
            { "width": "25%", "targets": 3 }, // Nombre
            { "width": "7%", "targets": 4 }, // Bloque
            { "width": "8%", "targets": 5 }, // Criticidad
            { "width": "6%", "targets": 6 }, // Estado
            { "width": "25%", "targets": 7 } // Descripción
        ],
        // =======================================================
        "drawCallback": function(settings) {
            var api = this.api();
            var filteredCount = api.page.info().recordsDisplay;
            var totalRegistrosDB = $('#tabla-aplicaciones').data('total-registros');
            var infoContainer = $('#tabla-aplicaciones_info');

            // Limpiar contadores personalizados anteriores para evitar duplicados
            infoContainer.find('.total-records-info, .filtered-records-info').remove();

            // Crear y añadir los nuevos contadores
            var totalInfo = '<div class="total-records-info">Total de registros existentes: <strong>' + totalRegistrosDB + '</strong></div>';
            var filteredInfo = '<div class="filtered-records-info">Registros encontrados (filtrados): <strong>' + filteredCount + '</strong></div>';
            infoContainer.append(totalInfo).append(filteredInfo);
        }
    });
});