# gestion/views/cod_cierre.py

import csv
import io
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils import no_cache, logger
from ..models import CodigoCierre, Aplicacion

# --- Vistas del CRUD para Códigos de Cierre ---


@login_required
@no_cache
def codigos_cierre_view(request):
    """
    Muestra la lista de códigos de cierre con opción de filtrado.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/cod_cierre.html' con el contexto.

    Context:
        'lista_de_codigos' (QuerySet): Códigos de cierre filtrados.
        'total_registros' (int): Conteo total de códigos en la BD.
        'todas_las_aplicaciones' (QuerySet): Lista de aplicaciones para el filtro.
    """
    logger.info(
        f"Usuario '{request.user}' está viendo la lista de códigos de cierre.")
    codigos_qs = CodigoCierre.objects.select_related('aplicacion').all()

    # Procesamiento de filtros
    filtro_codigo = request.GET.get('codigo_cierre')
    filtro_app_id = request.GET.get('aplicacion')
    filtros_aplicados = []

    if filtro_codigo:
        codigos_qs = codigos_qs.filter(cod_cierre__icontains=filtro_codigo)
        filtros_aplicados.append(f"código='{filtro_codigo}'")
    if filtro_app_id and filtro_app_id.isdigit():
        codigos_qs = codigos_qs.filter(aplicacion_id=filtro_app_id)
        filtros_aplicados.append(f"aplicacion_id='{filtro_app_id}'")

    if filtros_aplicados:
        logger.info(
            f"Búsqueda de códigos con filtros: {', '.join(filtros_aplicados)}.")

    context = {
        'lista_de_codigos': codigos_qs,
        'total_registros': CodigoCierre.objects.count(),
        'todas_las_aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
    }
    return render(request, 'gestion/cod_cierre.html', context)


@login_required
@no_cache
def registrar_cod_cierre_view(request):
    """
    Gestiona la creación de un nuevo código de cierre (vista GET y POST).

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza el formulario o redirige tras el registro.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta registrar un nuevo código de cierre.")
        id_aplicacion = request.POST.get('aplicacion')
        cod_cierre = request.POST.get('cod_cierre')
        # ... (obtención de otros campos)

        if not all([id_aplicacion, cod_cierre, ...]):  # Simplificado por brevedad
            logger.warning(
                f"Fallo de validación para '{request.user}': campos obligatorios vacíos.")
            messages.error(
                request, 'Error: Todos los campos son obligatorios.')
            return render(request, 'gestion/registrar_cod_cierre.html', {
                'todas_las_aplicaciones': Aplicacion.objects.all()
            })

        try:
            aplicacion_obj = Aplicacion.objects.get(pk=id_aplicacion)
            # ... (creación del objeto CodigoCierre)
            nuevo_codigo.save()
            logger.info(
                f"Usuario '{request.user}' registró con éxito el código '{cod_cierre}' para la app ID {id_aplicacion}.")
            messages.success(
                request, f'¡El código de cierre "{cod_cierre}" ha sido registrado con éxito!')
            return redirect('gestion:codigos_cierre')
        except Exception as e:
            logger.error(
                f"Error al registrar código de cierre por '{request.user}': {e}", exc_info=True)
            messages.error(request, f'Ocurrió un error inesperado: {e}')
            return redirect('gestion:registrar_cod_cierre')

    else:  # Método GET
        logger.info(
            f"Usuario '{request.user}' accedió al formulario de registro de código de cierre.")
        context = {'todas_las_aplicaciones': Aplicacion.objects.all()}
        return render(request, 'gestion/registrar_cod_cierre.html', context)


@login_required
@no_cache
def editar_cod_cierre_view(request, pk):
    """
    Gestiona la edición de un código de cierre existente (vista GET y POST).

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria del código a editar.

    Returns:
        HttpResponse: Renderiza el formulario o redirige tras la actualización.
    """
    try:
        codigo_a_editar = CodigoCierre.objects.get(pk=pk)
    except CodigoCierre.DoesNotExist:
        logger.warning(
            f"Usuario '{request.user}' intentó editar un código inexistente (ID: {pk}).")
        messages.error(
            request, 'El código de cierre que intentas editar no existe.')
        return redirect('gestion:codigos_cierre')

    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta actualizar el código de cierre ID: {pk}.")
        try:
            # ... (lógica de actualización de campos)
            codigo_a_editar.save()
            logger.info(
                f"Usuario '{request.user}' actualizó con éxito el código '{codigo_a_editar.cod_cierre}' (ID: {pk}).")
            messages.success(
                request, f'El código de cierre "{codigo_a_editar.cod_cierre}" ha sido actualizado.')
            return redirect('gestion:codigos_cierre')
        except Exception as e:
            logger.error(
                f"Error al actualizar el código de cierre ID {pk} por '{request.user}': {e}", exc_info=True)
            messages.error(request, f'Ocurrió un error al actualizar: {e}')
            return redirect('gestion:editar_cod_cierre', pk=pk)
    else:  # Método GET
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar el código ID: {pk}.")
        context = {
            'codigo_cierre': codigo_a_editar,
            'todas_las_aplicaciones': Aplicacion.objects.all()
        }
        return render(request, 'gestion/registrar_cod_cierre.html', context)


@login_required
@no_cache
def eliminar_cod_cierre_view(request, pk):
    """
    Elimina un código de cierre específico. Solo permite peticiones POST.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria del código a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la lista de códigos de cierre.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta eliminar el código de cierre ID: {pk}.")
        try:
            codigo_a_eliminar = CodigoCierre.objects.get(pk=pk)
            nombre_codigo = codigo_a_eliminar.cod_cierre
            codigo_a_eliminar.delete()
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO el código '{nombre_codigo}' (ID: {pk}).")
            messages.success(
                request, f'El código de cierre "{nombre_codigo}" ha sido eliminado.')
        except CodigoCierre.DoesNotExist:
            logger.warning(
                f"Intento de eliminación fallido: código inexistente (ID: {pk}). Usuario: '{request.user}'.")
            messages.error(
                request, 'El código de cierre que intentas eliminar no existe.')
        except Exception as e:
            logger.error(
                f"Error al eliminar código de cierre ID {pk} por '{request.user}': {e}", exc_info=True)
            messages.error(request, f'Ocurrió un error al eliminar: {e}')

    return redirect('gestion:codigos_cierre')


# --- Vista de Carga Masiva ---

@login_required
@no_cache
def carga_masiva_cod_cierre_view(request):
    """
    Gestiona la carga masiva de códigos de cierre desde un archivo CSV.

    Valida el archivo, busca duplicados internos, procesa cada fila para
    crear o ignorar registros y presenta un resumen detallado.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla de carga masiva con los resultados.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' inició una carga masiva de códigos de cierre.")
        csv_file = request.FILES.get('csv_file')
        context = {}

        if not csv_file or not csv_file.name.endswith('.csv'):
            logger.warning(
                f"Carga masiva fallida para '{request.user}': Archivo no válido.")
            messages.error(
                request, 'Por favor, seleccione un archivo CSV válido.')
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

        try:
            # ... (la lógica de lectura, pre-validación y procesamiento se mantiene igual)
            # ... (se han añadido comentarios internos para mayor claridad)

            # Bucle de procesamiento principal
            for line_number, row in enumerate(all_rows, start=2):
                try:
                    # ... (lógica de get_or_create)
                    pass
                except Exception as e:
                    # Log de error por cada fila que falla
                    logger.error(
                        f"Error procesando fila {line_number} en carga masiva de códigos. Error: {e}", exc_info=True)
                    failed_rows.append(
                        {'line': line_number, 'row_data': ';'.join(row.values()), 'error': str(e)})

            # ... (lógica de resumen y mensajes al usuario)

            return render(request, 'gestion/carga_masiva_cod_cierre.html', context)

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO en carga masiva de códigos por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general e inesperado: {e}")
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

    return render(request, 'gestion/carga_masiva_cod_cierre.html')


# --- Vista para AJAX ---

def obtener_ultimos_codigos_cierre(request, aplicacion_id):
    """
    Endpoint API para ser llamado vía AJAX.

    Devuelve los 5 códigos de cierre más recientes para una aplicación específica,
    en formato JSON. Usado para asistir en la entrada de datos en otros formularios.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        aplicacion_id (int): El ID de la aplicación para la cual buscar códigos.

    Returns:
        JsonResponse: Un objeto JSON con una lista de códigos o un mensaje de error.
    """

    logger.info(
        f"Petición AJAX recibida para obtener códigos de la app ID: {aplicacion_id}.")
    try:
        codigos = CodigoCierre.objects.filter(
            aplicacion_id=aplicacion_id).order_by('-id')[:5]
        data = list(codigos.values('cod_cierre', 'desc_cod_cierre'))
        return JsonResponse({'codigos': data})
    except Exception as e:
        logger.error(
            f"Error en AJAX 'obtener_ultimos_codigos_cierre' para app_id {aplicacion_id}: {e}", exc_info=True)
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)
