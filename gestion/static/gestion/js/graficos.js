// gestion/static/gestion/js/graficos.js
Chart.register(ChartDataLabels);

/**
 * Módulo autocontenido para la página de Dashboard de Gráficos.
 * No depende de un objeto global 'App' y se autoinicializa.
 */
const dashboardModule = {
    // Propiedades para almacenar las instancias de los gráficos
    chartInstances: {
        aplicativo: null,
        porMes: null,
        severidad: null,
        porCodigoCierre: null
    },

    // URLs que necesita esta página específica
    urls: {},

    // Paletas de colores centralizadas para los gráficos
    colors: {
        porAplicativo: 'rgba(70, 130, 180, 0.7)',
        porMes: [
            '#8A2BE2', '#4682B4', '#20B2AA', '#FF69B4',
            '#6A5ACD', '#00CED1', '#DA70D6'
        ],
        porSeveridad: ['#14b13bff', '#FFD700', '#DC143C', '#FF8C00'],
        porCodigoCierre: {
            backgroundColor: 'rgba(0, 128, 128, 0.2)',
            borderColor: 'rgba(0, 128, 128, 1)'
        }
    },

    // Punto de entrada para la lógica del dashboard
    init: function() {
        console.log("Inicializando módulo de Dashboard...");
        const pageContainer = document.querySelector('.page-container');
        if (!pageContainer) return;

        this.urls = {
            graficosData: pageContainer.dataset.urlGraficosData,
            codigosCierre: pageContainer.dataset.urlCodigosCierre
        };
        this.addEventListeners();
        this.actualizarGraficos();
    },

    // Centralizamos todos los event listeners
    addEventListeners: function() {
        $('#toggle-filters-btn').on('click', function() {
            var filterContainer = $('#filter-container');
            if (filterContainer.is(':visible')) {
                filterContainer.slideUp();
                $(this).text('Mostrar Filtros');
            } else {
                filterContainer.slideDown();
                $(this).text('Ocultar Filtros');
            }
        });

        $('#graficos-filters-form').on('submit', (e) => {
            e.preventDefault();
            this.actualizarGraficos();
        });

        $('#limpiar-filtros-btn').on('click', () => {
            $('#graficos-filters-form')[0].reset();
            $('#aplicativo').trigger('change');
            this.actualizarGraficos();
        });

        $('#aplicativo').on('change', () => {
            this.cargarCodigosCierre();
        });
    },

    // Lógica para renderizar o actualizar un gráfico
    renderChart: function(canvasId, chartKey, chartData, chartTitle, datasetLabel, colorPalette, chartType = 'bar') {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (this.chartInstances[chartKey]) {
            this.chartInstances[chartKey].destroy();
        }

        const isRadialChart = ['pie', 'doughnut', 'polarArea'].includes(chartType);

        const datasetConfig = {
            label: datasetLabel,
            data: chartData.values,
            borderWidth: 1
        };

        if (chartType === 'line') {
            datasetConfig.backgroundColor = colorPalette.backgroundColor;
            datasetConfig.borderColor = colorPalette.borderColor;
            datasetConfig.fill = true;
            datasetConfig.tension = 0.1;
        } else {
            datasetConfig.backgroundColor = colorPalette;
            datasetConfig.borderColor = isRadialChart ? '#2c2f33' : 'rgba(0,0,0,0.2)';
        }

        this.chartInstances[chartKey] = new Chart(ctx, {
            type: chartType,
            data: {
                labels: chartData.labels,
                datasets: [datasetConfig]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,

                // --- INICIO: MODIFICACIÓN DE ESCALAS ---
                scales: isRadialChart ? {
                    // 'r' es el eje radial para gráficos polares
                    r: {
                        // Color de las líneas circulares (la "telaraña")
                        grid: {
                            color: 'rgba(255, 255, 255, 0.2)'
                        },
                        // Color de las líneas que van del centro hacia afuera
                        angleLines: {
                            color: 'rgba(255, 255, 255, 0.2)'
                        },
                        // Color de las etiquetas de los puntos (ej: "Abril 2025")
                        pointLabels: {
                            color: '#FFFFFF'
                        },
                        // Estilos para los números de la escala (ej: 50, 100, 150)
                        ticks: {
                            color: '#E0E0E0',
                            backdropColor: 'rgba(0, 0, 0, 0.5)', // Fondo para que los números resalten
                            backdropPadding: 2
                        }
                    }
                } : {
                    // Configuración para gráficos no-radiales (barras, líneas)
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0, color: '#E0E0E0' }
                    },
                    x: { ticks: { color: '#E0E0E0' } }
                },
                // --- FIN: MODIFICACIÓN DE ESCALAS ---

                plugins: {
                    title: {
                        display: true,
                        text: chartTitle,
                        font: { size: 18 },
                        padding: { bottom: 20 },
                        color: '#FFFFFF'
                    },
                    legend: {
                        labels: { color: '#B0B0B0' }
                    },
                    datalabels: {
                        display: function(context) {
                            return context.dataset.data[context.dataIndex] > 0;
                        },
                        formatter: (value) => new Intl.NumberFormat('es-ES').format(value),
                        color: '#FFFFFF',
                        font: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return {
                                weight: 'bold',
                                size: isRadial ? 16 : 13
                            };
                        },
                        backgroundColor: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'rgba(0, 0, 0, 0.5)' : null;
                        },
                        borderRadius: 5,
                        padding: 4,
                        anchor: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'center' : 'end';
                        },
                        align: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'center' : 'top';
                        },
                        offset: 8
                    }
                }
            }
        });
    },

    // Lógica para obtener datos y actualizar todos los gráficos
    actualizarGraficos: function() {
        const form = $('#graficos-filters-form');
        const url = `${this.urls.graficosData}?${form.serialize()}`;
        const spinner = document.getElementById('loading-spinner');

        if (spinner) spinner.style.display = 'flex';

        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('La respuesta del servidor no fue exitosa.');
                return response.json();
            })
            .then(data => {
                $('#total-general-valor').text((data.total_general || 0).toLocaleString('es-ES'));
                $('#total-filtrado-valor').text((data.total_filtrado || 0).toLocaleString('es-ES'));

                if (data && data.por_aplicativo) {
                    this.renderChart('chartPorAplicativo', 'aplicativo', data.por_aplicativo, 'Incidencias por Aplicativo (Top 15)', 'Nº de Incidencias', this.colors.porAplicativo, 'bar');
                }
                if (data && data.por_mes) {
                    this.renderChart('chartPorMes', 'porMes', data.por_mes, 'Incidencias por Mes', 'Nº de Incidencias', this.colors.porMes, 'polarArea');
                }
                if (data && data.por_severidad) {
                    this.renderChart('chartPorSeveridad', 'severidad', data.por_severidad, 'Incidencias por Severidad', 'Nº de Incidencias', this.colors.porSeveridad, 'pie');
                }
                if (data && data.por_codigo_cierre) {
                    this.renderChart('chartPorCodigoCierre', 'porCodigoCierre', data.por_codigo_cierre, 'Top 15 Códigos de Cierre', 'Nº de Incidencias', this.colors.porCodigoCierre, 'line');
                }

                if (spinner) spinner.style.display = 'none';
            })
            .catch(error => {
                console.error('Error al cargar datos de los gráficos:', error);
                if (spinner) spinner.style.display = 'none';
                alert('No se pudieron cargar los datos para los gráficos.');
            });
    },

    // Lógica para cargar dinámicamente los códigos de cierre
    cargarCodigosCierre: function() {
        const aplicativoId = $('#aplicativo').val();
        const codigoCierreSelect = $('#codigo_cierre');
        const url = `${this.urls.codigosCierre}?aplicativo_id=${aplicativoId}`;

        codigoCierreSelect.html('<option value="">Cargando...</option>').prop('disabled', true);

        fetch(url)
            .then(response => response.json())
            .then(data => {
                codigoCierreSelect.html('<option value="">Todos</option>').prop('disabled', false);
                data.codigos.forEach(codigo => {
                    codigoCierreSelect.append($('<option></option>').val(codigo.id).text(codigo.text));
                });
            })
            .catch(error => {
                console.error('Error al cargar los códigos de cierre:', error);
                codigoCierreSelect.html('<option value="">Error al cargar</option>').prop('disabled', true);
            });
    }
};

$(document).ready(function() {
    dashboardModule.init();
});