// gestion\static\gestion\js\incidencia.js

/**
 * Convierte una cadena de tiempo de SLA (ej. "1 día, 4:05:10" o "8:30:00")
 * al formato hh:mm:ss (ej. "28:05:10" o "08:30:00").
 * @param {string} slaString - La cadena de tiempo a formatear.
 * @returns {string} El tiempo formateado o el valor original si no se puede procesar.
 */
function formatSlaToHHMMSS(slaString) {
    if (!slaString || slaString.trim().toLowerCase() === 'n/a') {
        return 'N/A';
    }

    let totalHours = 0;
    let timePart = slaString.trim();

    // Busca si la cadena contiene días
    if (timePart.includes('día') || timePart.includes('day')) {
        const parts = timePart.split(',');
        const dayPart = parts[0];
        timePart = parts.length > 1 ? parts[1].trim() : '0:0:0';

        const days = parseInt(dayPart, 10); // parseInt extrae el número inicial
        if (!isNaN(days)) {
            totalHours += days * 24;
        }
    }

    const timeComponents = timePart.split(':');
    if (timeComponents.length === 3) {
        totalHours += parseInt(timeComponents[0], 10);
        const minutes = String(timeComponents[1]).padStart(2, '0');
        const seconds = String(timeComponents[2]).padStart(2, '0');
        return `${String(totalHours).padStart(2, '0')}:${minutes}:${seconds}`;
    }
    return slaString; // Devuelve el original si el formato no es el esperado
}

$(document).ready(function() {
    // Se lee el total de registros desde el atributo data-* de la tabla
    const totalRegistrosDB = $('#tabla-incidencias').data('total-registros') || 0;

    var table = $('#tabla-incidencias').DataTable({
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de un total de _MAX_ registros)",
            "search": "Buscar:",
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
        "width": "100%",
        "scrollY": "48vh",
        "scrollCollapse": true,
        "paging": true,
        "pageLength": 25,
        "order": [
            [2, "asc"]
        ],
        "columnDefs": [
            { "width": "3%", "targets": 1 },
            { "width": "4%", "targets": [0, 1, 2] },
            { "width": "6%", "targets": [3, 4, 6] },
            { "width": "7%", "targets": 8 }
        ],
        "initComplete": function(settings, json) {
            $('#tabla-incidencias').removeClass('data-table-loading');
        },
        "drawCallback": function(settings) {
            var api = this.api();
            var filteredCount = api.page.info().recordsDisplay;
            var infoContainer = $('#tabla-incidencias_info');
            var filteredInfo = '<div class="filtered-records-info">Registros encontrados (filtrados): <strong>' + filteredCount + '</strong></div>';
            var totalInfo = '<div class="total-records-info">Total de registros existentes: <strong>' + totalRegistrosDB + '</strong></div>';

            infoContainer.find('.filtered-records-info').remove();
            infoContainer.find('.total-records-info').remove();
            infoContainer.append(totalInfo);
            infoContainer.append(filteredInfo);

            // Formatear el tiempo SLA en cada redibujado de la tabla
            $('.celda-tiempo-sla', api.table().body()).each(function() {
                var originalText = $(this).text().trim();
                $(this).text(formatSlaToHHMMSS(originalText));
            });
        }
    });

    // Script para el botón de mostrar/ocultar filtros
    $('#toggle-filters-btn').on('click', function(event) {
        var filterContainer = $('#filter-container');
        if (filterContainer.is(':visible')) {
            filterContainer.slideUp();
            $(this).text('Mostrar Filtros');
        } else {
            filterContainer.slideDown(function() {
                table.columns.adjust().draw();
            });
            $(this).text('Ocultar Filtros');
        }
    });

    // Script para el botón de limpiar filtros
    $('#limpiar-filtros-btn').on('click', function() {
        var form = $(this).closest('form');
        form.find('input[type="text"], input[type="date"]').val('');
        form.find('select').prop('selectedIndex', 0);
    });

    // Lógica para el checkbox "Seleccionar Todo"
    $('#select-all-checkbox').on('click', function() {
        $('.incidencia-checkbox').prop('checked', this.checked);
    });

    // Lógica para el botón "Asignar SLA"
    $('#btn-asignar-sla').on('click', function() {
        var selected_ids = [];
        $('.incidencia-checkbox:checked').each(function() {
            selected_ids.push($(this).val());
        });

        if (selected_ids.length === 0) {
            alert('Por favor, selecciona al menos una incidencia para calcular el SLA.');
            return;
        }

        $('#loading-spinner').css('display', 'flex');

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        const csrftoken = getCookie('csrftoken');

        // Se obtiene la URL del atributo data-url del botón
        const url = $(this).data('url');

        fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    'incidencia_ids': selected_ids
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    data.results.forEach(function(result) {
                        var fila = $('tr[data-incidencia-id="' + result.id + '"]');
                        fila.find('.celda-cumple-sla').text(result.cumple_sla);
                        fila.find('.celda-tiempo-sla').text(formatSlaToHHMMSS(result.tiempo_sla));
                    });
                } else {
                    alert('Error: ' + data.message);
                }
                $('#loading-spinner').hide();
            })
            .catch(error => {
                console.error('Error en la petición AJAX:', error);
                alert('Ocurrió un error de comunicación con el servidor.');
                $('#loading-spinner').hide();
            });
    });

    // Código para exportar CSV
    $('#btn-exportar-csv').on('click', function() {
        var incidencia = $('#incidencia').val();
        var fechaDesde = $('#fecha_desde').val();
        var fechaHasta = $('#fecha_hasta').val();

        // Se obtiene la URL base del atributo data-url del botón
        var url = new URL($(this).data('url'), window.location.origin);

        if (incidencia) url.searchParams.append('incidencia', incidencia);
        if (fechaDesde) url.searchParams.append('fecha_desde', fechaDesde);
        if (fechaHasta) url.searchParams.append('fecha_hasta', fechaHasta);

        console.log("Iniciando descarga desde: " + url.href);
        window.location.href = url.href;
    });

    // Código para exportar reporte Excel
    $('#btn-exportar-reporte').on('click', function() {
        var incidencia = $('#incidencia').val();
        var aplicativo = $('#aplicativo').val();
        var bloque = $('#bloque').val();
        var codigoCierre = $('#codigo_cierre').val();
        var fechaDesde = $('#fecha_desde').val();
        var fechaHasta = $('#fecha_hasta').val();

        // Se obtiene la URL base del atributo data-url del botón
        var url = new URL($(this).data('url'), window.location.origin);

        if (incidencia) url.searchParams.append('incidencia', incidencia);
        if (aplicativo) url.searchParams.append('aplicativo', aplicativo);
        if (bloque) url.searchParams.append('bloque', bloque);
        if (codigoCierre) url.searchParams.append('codigo_cierre', codigoCierre);
        if (fechaDesde) url.searchParams.append('fecha_desde', fechaDesde);
        if (fechaHasta) url.searchParams.append('fecha_hasta', fechaHasta);

        console.log("Iniciando descarga de reporte Excel desde: " + url.href);
        window.location.href = url.href;
    });
});