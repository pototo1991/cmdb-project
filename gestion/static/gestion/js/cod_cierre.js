// gestion\static\gestion\js\cod_cierre.js

// gestion/static/gestion/js/cod_cierre.js

$(document).ready(function() {
    $('#tabla-codigos-cierre').DataTable({
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de un total de _MAX_ registros)",
            "search": "Buscar por:",
            "paginate": {
                "first": "Primero",
                "last": "Último",
                "next": "Siguiente",
                "previous": "Anterior"
            }
        },
        "lengthMenu": [
            [10, 25, 50, 100, -1],
            [10, 25, 50, 100, "Todas"]
        ],
        "scrollY": "60vh",
        "scrollCollapse": true,
        "paging": true,
        "pageLength": 25,
        "order": [
            [2, "asc"]
        ],
        "columnDefs": [
            { "width": "5%", "targets": [0, 1] }, // Eliminar y Editar
            { "width": "10%", "targets": 2 }, // Código de Cierre
            { "width": "10%", "targets": 3 }, // Aplicación
            { "width": "30%", "targets": 4 }, // Descripción
            { "width": "30%", "targets": 5 } // Causa de Cierre
        ],
        "initComplete": function(settings, json) {
            $('#tabla-codigos-cierre').removeClass('data-table-loading');
        },
        "drawCallback": function(settings) {
            var api = this.api();
            var filteredCount = api.page.info().recordsDisplay;
            var totalRegistrosDB = parseInt($('#tabla-codigos-cierre').data('total-registros')) || 0; // Se obtiene del atributo data-*

            var infoContainer = $('#tabla-codigos-cierre_info');

            var filteredInfo = '<div class="filtered-records-info">Registros encontrados (filtrados): <strong>' + filteredCount + '</strong></div>';
            var totalInfo = '<div class="total-records-info">Total de registros existentes: <strong>' + totalRegistrosDB + '</strong></div>';

            infoContainer.find('.filtered-records-info').remove();
            infoContainer.find('.total-records-info').remove();

            infoContainer.append(totalInfo);
            infoContainer.append(filteredInfo);
        }
    });
    // Maneja el clic en el botón para mostrar u ocultar los filtros
    $('#toggle-filters-btn').on('click', function() {
        const filterContainer = $('#filter-container');
        if (filterContainer.is(':visible')) {
            filterContainer.slideUp();
            $(this).text('Mostrar Filtros');
        } else {
            filterContainer.slideDown();
            $(this).text('Ocultar Filtros');
        }
    });

    // Maneja el clic en el botón para limpiar los campos del filtro
    $('#limpiar-filtros-btn').on('click', function() {
        const form = $(this).closest('form');
        form.find('input[type="text"]').val('');
        form.find('select').prop('selectedIndex', 0);
    });
});