# gestion/views/incidencias.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils import no_cache, logger
from ..models import Aplicacion, Estado, Severidad, Impacto, GrupoResolutor, Interfaz, Cluster, Bloque, Incidencia, CodigoCierre


@login_required
@no_cache
def incidencias_view(request):
    """Maneja la lógica para la página de gestión de incidencias."""
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de incidencias.")
    incidencias = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque'
    ).all()
    total_registros = incidencias.count()
    context = {
        'lista_de_incidencias': incidencias,
        'total_registros': total_registros,
    }
    return render(request, 'gestion/incidencia.html', context)


@login_required
@no_cache
def registrar_incidencia_view(request):
    """
    Gestiona el registro de una nueva incidencia, incluyendo todos los campos manuales.
    (Versión completa y corregida).
    """

    # Función auxiliar para cargar el contexto del formulario
    def get_context_data():
        return {
            'aplicaciones': Aplicacion.objects.all(),
            'estados': Estado.objects.all(),
            'severidades': Severidad.objects.all(),
            'impactos': Impacto.objects.all(),
            'grupos_resolutores': GrupoResolutor.objects.all(),
            'interfaces': Interfaz.objects.all(),
            'clusters': Cluster.objects.all(),
            'bloques': Bloque.objects.all(),
            'codigos_cierre': CodigoCierre.objects.all(),
        }

    # --- PROCESAMIENTO DEL FORMULARIO (MÉTODO POST) ---
    if request.method == 'POST':
        try:
            # Obtener instancias de FK obligatorias
            aplicacion_obj = Aplicacion.objects.get(
                pk=request.POST.get('aplicacion'))
            estado_obj = Estado.objects.get(pk=request.POST.get('estado'))
            impacto_obj = Impacto.objects.get(pk=request.POST.get('impacto'))
            bloque_obj = Bloque.objects.get(pk=request.POST.get('bloque'))

            # Obtener instancias de FK opcionales
            severidad_obj = Severidad.objects.get(pk=request.POST.get(
                'severidad')) if request.POST.get('severidad') else None
            grupo_resolutor_obj = GrupoResolutor.objects.get(pk=request.POST.get(
                'grupo_resolutor')) if request.POST.get('grupo_resolutor') else None
            interfaz_obj = Interfaz.objects.get(pk=request.POST.get(
                'interfaz')) if request.POST.get('interfaz') else None
            cluster_obj = Cluster.objects.get(pk=request.POST.get(
                'cluster')) if request.POST.get('cluster') else None
            codigo_cierre_obj = CodigoCierre.objects.get(pk=request.POST.get(
                'codigo_cierre')) if request.POST.get('codigo_cierre') else None

            # Manejo de campos de fecha (pueden estar vacíos)
            fecha_apertura_str = request.POST.get('fecha_apertura')
            fecha_apertura_obj = datetime.fromisoformat(
                fecha_apertura_str) if fecha_apertura_str else None
            fecha_resolucion_str = request.POST.get('fecha_ultima_resolucion')
            fecha_resolucion_obj = datetime.fromisoformat(
                fecha_resolucion_str) if fecha_resolucion_str else None

            # Manejo de workaround (ahora es un campo de texto 'Sí'/'No')
            workaround_val = request.POST.get('workaround', 'No')
            # Creación del objeto Incidencia
            nueva_incidencia = Incidencia(
                incidencia=request.POST.get('incidencia'),
                descripcion_incidencia=request.POST.get(
                    'descripcion_incidencia', ''),
                fecha_apertura=fecha_apertura_obj,
                fecha_ultima_resolucion=fecha_resolucion_obj,
                causa=request.POST.get('causa', ''),
                bitacora=request.POST.get('bitacora', ''),
                tec_analisis=request.POST.get('tec_analisis', ''),
                correccion=request.POST.get('correccion', ''),
                solucion_final=request.POST.get('solucion_final', ''),
                observaciones=request.POST.get('observaciones', ''),
                usuario_asignado=request.POST.get('usuario_asignado', ''),
                demandas=request.POST.get('demandas', ''),
                workaround=workaround_val,
                aplicacion=aplicacion_obj,
                estado=estado_obj,
                severidad=severidad_obj,
                grupo_resolutor=grupo_resolutor_obj,
                interfaz=interfaz_obj,
                impacto=impacto_obj,
                cluster=cluster_obj,
                bloque=bloque_obj,
                codigo_cierre=codigo_cierre_obj,
            )
            nueva_incidencia.save()

            logger.info(
                f"Usuario '{request.user}' registró la nueva incidencia '{nueva_incidencia.incidencia}'.")
            messages.success(
                request, f'¡La incidencia "{nueva_incidencia.incidencia}" ha sido registrada con éxito!')
            return redirect('gestion:incidencias')

        except Exception as e:
            logger.error(
                f"Error al registrar incidencia por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error inesperado al guardar la incidencia: {e}. Por favor, revisa los datos.')
            # En caso de error, volvemos a renderizar el formulario con los datos para no perderlos
            context = get_context_data()
            # Opcional: para rellenar el formulario
            context['form_data'] = request.POST
            return render(request, 'gestion/registrar_incidencia.html', context)

    # --- CARGA INICIAL DE LA PÁGINA (MÉTODO GET) ---
    else:
        try:
            context = get_context_data()
            # Este return es el que probablemente faltaba o estaba en el lugar incorrecto
            return render(request, 'gestion/registrar_incidencia.html', context)
        except Exception as e:
            logger.error(
                f"Error al cargar datos para el formulario de registro: {e}", exc_info=True)
            messages.error(
                request, 'Ocurrió un error al cargar la página de registro.')
            # Redirigir a un lugar seguro en caso de error
            return redirect('gestion:dashboard')
