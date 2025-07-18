# gestion/views/incidencias.py

from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from .utils import no_cache, logger
from ..models import Aplicacion, Estado, Severidad, Impacto, GrupoResolutor, Interfaz, Cluster, Bloque, Incidencia, CodigoCierre, Usuario


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
            # <--- 2. AÑADIMOS LA LISTA DE USUARIOS AL CONTEXTO
            'usuarios': Usuario.objects.all().order_by('nombre'),
        }

    if request.method == 'POST':
        try:
            aplicacion_obj = Aplicacion.objects.get(
                pk=request.POST.get('aplicacion'))
            estado_obj = Estado.objects.get(pk=request.POST.get('estado'))
            impacto_obj = Impacto.objects.get(pk=request.POST.get('impacto'))
            bloque_obj = Bloque.objects.get(pk=request.POST.get('bloque'))

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

            # 👇 3. PROCESAMOS CORRECTAMENTE EL USUARIO SELECCIONADO
            usuario_asignado_obj = Usuario.objects.get(pk=request.POST.get(
                'usuario_asignado')) if request.POST.get('usuario_asignado') else None

            fecha_apertura_str = request.POST.get('fecha_apertura')
            fecha_apertura_obj = datetime.fromisoformat(
                fecha_apertura_str) if fecha_apertura_str else None
            fecha_resolucion_str = request.POST.get('fecha_ultima_resolucion')
            fecha_resolucion_obj = datetime.fromisoformat(
                fecha_resolucion_str) if fecha_resolucion_str else None

            workaround_val = request.POST.get('workaround', 'No')

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
                # <--- 3. (cont.) USAMOS EL OBJETO OBTENIDO
                usuario_asignado=usuario_asignado_obj,
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
            context = get_context_data()
            context['form_data'] = request.POST
            return render(request, 'gestion/registrar_incidencia.html', context)

    else:
        try:
            context = get_context_data()
            return render(request, 'gestion/registrar_incidencia.html', context)
        except Exception as e:
            logger.error(
                f"Error al cargar datos para el formulario de registro: {e}", exc_info=True)
            messages.error(
                request, 'Ocurrió un error al cargar la página de registro.')
            return redirect('gestion:dashboard')


# 👇 AÑADIMOS LA NUEVA VISTA PARA EDITAR 👇
@login_required
@no_cache
def editar_incidencia_view(request, pk):
    """
    Gestiona la edición de una incidencia existente.
    Reutiliza la plantilla de 'registrar_incidencia.html'.
    """
    # Obtenemos la incidencia que se va a editar o mostramos un error 404 si no existe
    incidencia = get_object_or_404(Incidencia, pk=pk)

    # La función para obtener los datos de los selectores es la misma que en registrar
    def get_context_data():
        # Obtenemos todos los códigos de cierre para la aplicación actual
        codigos_cierre_app = CodigoCierre.objects.filter(
            aplicacion=incidencia.aplicacion)

        return {
            'aplicaciones': Aplicacion.objects.all(),
            'estados': Estado.objects.all(),
            'severidades': Severidad.objects.all(),
            'impactos': Impacto.objects.all(),
            'grupos_resolutores': GrupoResolutor.objects.all(),
            'interfaces': Interfaz.objects.all(),
            'clusters': Cluster.objects.all(),
            'bloques': Bloque.objects.all(),
            'usuarios': Usuario.objects.all().order_by('nombre'),
            'codigos_cierre': codigos_cierre_app,  # Pasamos los códigos de cierre filtrados
        }

    if request.method == 'POST':
        # El proceso de guardar es similar a registrar, pero actualizamos el objeto existente
        try:
            # Actualizamos los campos del objeto 'incidencia' con los datos del formulario
            incidencia.incidencia = request.POST.get('incidencia')
            incidencia.descripcion_incidencia = request.POST.get(
                'descripcion_incidencia', '')

            # ... (se actualizan todos los demás campos de la misma forma) ...

            # Guardamos los cambios en la base de datos
            incidencia.save()

            messages.success(
                request, f'¡La incidencia "{incidencia.incidencia}" ha sido actualizada con éxito!')
            return redirect('gestion:incidencias')

        except Exception as e:
            logger.error(
                f"Error al editar incidencia '{incidencia.id}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al actualizar la incidencia: {e}')

            context = get_context_data()
            # Reenviamos la incidencia al contexto
            context['incidencia'] = incidencia
            return render(request, 'gestion/registrar_incidencia.html', context)

    else:  # Si es método GET, mostramos el formulario con los datos actuales
        context = get_context_data()
        # Añadimos la incidencia al contexto
        context['incidencia'] = incidencia
        return render(request, 'gestion/registrar_incidencia.html', context)


# 👇 AÑADIMOS LA NUEVA VISTA PARA ELIMINAR 👇
@login_required
@no_cache
def eliminar_incidencia_view(request, pk):
    """
    Elimina una incidencia. Solo acepta peticiones POST por seguridad.
    """
    if request.method == 'POST':
        try:
            incidencia = get_object_or_404(Incidencia, pk=pk)
            nombre_incidencia = incidencia.incidencia
            incidencia.delete()
            messages.success(
                request, f'La incidencia "{nombre_incidencia}" ha sido eliminada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la incidencia: {e}')

    # Redirigimos siempre a la lista de incidencias
    return redirect('gestion:incidencias')


@login_required
@no_cache
def get_codigos_cierre_por_aplicacion(request, aplicacion_id):
    """
    Vista que, dado un ID de aplicación, devuelve los códigos de cierre 
    asociados en formato JSON.
    """
    try:
        # Usamos .annotate() para crear alias que coincidan con lo que el JavaScript espera ('codigo' y 'descripcion')
        codigos = CodigoCierre.objects.filter(aplicacion_id=aplicacion_id).annotate(
            codigo=F('cod_cierre'),
            descripcion=F('desc_cod_cierre')
        ).order_by('codigo').values('id', 'codigo', 'descripcion')

        return JsonResponse(list(codigos), safe=False)

    except Exception as e:
        logger.error(
            f"Error en get_codigos_cierre_por_aplicacion: {e}", exc_info=True)
        return JsonResponse({'error': 'Ocurrió un error en el servidor.'}, status=500)
