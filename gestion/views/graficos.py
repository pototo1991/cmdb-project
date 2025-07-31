# gestion/views/graficos.py

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required
from .utils import no_cache
from ..models import Incidencia, Aplicacion, Bloque, Estado, Severidad, CodigoCierre, Usuario


def get_filtered_incidencias(request):
    """
    Función auxiliar para filtrar incidencias basada en los parámetros GET.
    """
    queryset = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'bloque', 'severidad', 'codigo_cierre', 'usuario_asignado'
    ).all()

    if aplicativo_id := request.GET.get('aplicativo'):
        queryset = queryset.filter(aplicacion_id=aplicativo_id)
    if bloque_id := request.GET.get('bloque'):
        queryset = queryset.filter(bloque_id=bloque_id)
    if fecha_desde := request.GET.get('fecha_desde'):
        queryset = queryset.filter(fecha_ultima_resolucion__gte=fecha_desde)
    if fecha_hasta := request.GET.get('fecha_hasta'):
        queryset = queryset.filter(fecha_ultima_resolucion__lte=fecha_hasta)
    if severidad_id := request.GET.get('severidad'):
        queryset = queryset.filter(severidad_id=severidad_id)
    if year := request.GET.get('year'):
        queryset = queryset.filter(fecha_ultima_resolucion__year=year)
    if month := request.GET.get('month'):
        queryset = queryset.filter(fecha_ultima_resolucion__month=month)
    if codigo_cierre_id := request.GET.get('codigo_cierre'):
        queryset = queryset.filter(codigo_cierre_id=codigo_cierre_id)
    if usuario_id := request.GET.get('usuario'):
        queryset = queryset.filter(usuario_asignado_id=usuario_id)

    return queryset


@login_required
@no_cache
def graficos_view(request):
    """
    Renderiza la página de gráficos y pasa los datos para los selectores de filtro.
    """
    aplicaciones = Aplicacion.objects.all().order_by('nombre_aplicacion')
    bloques = Bloque.objects.all().order_by('desc_bloque')
    severidades = Severidad.objects.all().order_by('desc_severidad')
    codigos_cierre = CodigoCierre.objects.all().order_by('cod_cierre')
    usuarios = Usuario.objects.all().order_by('nombre')

    # Obtenemos los años únicos donde hay incidencias para el filtro
    years = Incidencia.objects.filter(fecha_ultima_resolucion__isnull=False).dates(
        'fecha_ultima_resolucion', 'year', order='DESC')
    months = [
        {'value': 1, 'name': 'Enero'}, {'value': 2, 'name': 'Febrero'},
        {'value': 3, 'name': 'Marzo'}, {'value': 4, 'name': 'Abril'},
        {'value': 5, 'name': 'Mayo'}, {'value': 6, 'name': 'Junio'},
        {'value': 7, 'name': 'Julio'}, {'value': 8, 'name': 'Agosto'},
        {'value': 9, 'name': 'Septiembre'}, {'value': 10, 'name': 'Octubre'},
        {'value': 11, 'name': 'Noviembre'}, {'value': 12, 'name': 'Diciembre'},
    ]

    context = {
        'aplicaciones': aplicaciones,
        'bloques': bloques,
        'severidades': severidades,
        'codigos_cierre': codigos_cierre,
        'usuarios': usuarios,
        'years': years,
        'months': months,
    }
    return render(request, 'gestion/graficos.html', context)


@login_required
@no_cache
def graficos_data_json(request):
    """
    Devuelve los datos agregados para los gráficos en formato JSON.
    """
    incidencias_filtradas = get_filtered_incidencias(request)

    # Calculamos el total de incidencias filtradas
    total_incidencias = incidencias_filtradas.count()

    # Gráfico 1: Incidencias por Aplicativo
    data_aplicativo = (
        incidencias_filtradas
        .values('aplicacion__nombre_aplicacion')
        .annotate(total=Count('id'))
        .order_by('-total')[:15]  # Mostramos solo los 15 principales
    )

    # Gráfico 2: Incidencias por mes
    data_por_mes = (
        incidencias_filtradas
        .annotate(mes=TruncMonth('fecha_ultima_resolucion'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    # Gráfico 3: Incidencias por Severidad
    data_severidad = (
        incidencias_filtradas
        .values('severidad__desc_severidad')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Gráfico 4: Top 15 Códigos de Cierre más recurrentes
    data_codigos_cierre = (
        incidencias_filtradas
        .values('codigo_cierre__cod_cierre')
        .annotate(total=Count('id'))
        .order_by('-total')[:15]
    )

    # Diccionario para asegurar nombres de meses en español
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    chart_data = {
        'total_incidencias': total_incidencias,
        'por_aplicativo': {'labels': [item['aplicacion__nombre_aplicacion'] or "No Asignado" for item in data_aplicativo], 'values': [item['total'] for item in data_aplicativo]},
        'por_mes': {
            'labels': [f"{meses_es.get(item['mes'].month, '')} {item['mes'].year}" for item in data_por_mes if item['mes']],
            'values': [item['total'] for item in data_por_mes if item['mes']]
        },
        'por_severidad': {'labels': [item['severidad__desc_severidad'] or "Sin Severidad" for item in data_severidad], 'values': [item['total'] for item in data_severidad]},
        'por_codigo_cierre': {
            'labels': [item['codigo_cierre__cod_cierre'] or "No Asignado" for item in data_codigos_cierre],
            'values': [item['total'] for item in data_codigos_cierre]
        }
    }

    return JsonResponse(chart_data)


@login_required
def get_codigos_cierre_ajax(request):
    """
    Devuelve una lista de Códigos de Cierre en JSON,
    filtrada por un aplicativo si se proporciona su ID.
    """
    aplicativo_id = request.GET.get('aplicativo_id')

    if aplicativo_id:
        codigos = CodigoCierre.objects.filter(
            aplicacion_id=aplicativo_id).order_by('cod_cierre')
    else:
        # Si no se especifica un aplicativo, devolver todos los códigos
        codigos = CodigoCierre.objects.all().order_by('cod_cierre')

    data = [{'id': c.id, 'text': c.cod_cierre} for c in codigos]
    return JsonResponse({'codigos': data})
