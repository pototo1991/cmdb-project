# gestion/views/cod_cierre.py

import csv
import io
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q  # <-- AÑADIDO: Importante para búsquedas complejas
from .utils import no_cache, logger
from ..models import CodigoCierre, Aplicacion


@login_required
@no_cache
def codigos_cierre_view(request):
    """
    Muestra la lista de códigos de cierre, aplicando los filtros que lleguen por GET.
    """
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de códigos de cierre.")

    # Obtener los valores de los filtros desde la URL
    filtro_cod = request.GET.get('cod_cierre', '')
    filtro_app_id = request.GET.get('aplicacion', '')

    # --- INICIO DE LA CORRECCIÓN ---

    # 1. Empezar con todos los códigos.
    codigos_query = CodigoCierre.objects.select_related('aplicacion').all()

    # 2. Contar el total de registros ANTES de aplicar cualquier filtro.
    #    Este es el valor que será fijo en la interfaz.
    total_registros_db = codigos_query.count()  # <-- CAMBIO CLAVE

    # 3. Ahora, aplicar los filtros sobre el query para la tabla.
    if filtro_cod:
        # Busca el texto en el código de cierre O en la descripción
        codigos_query = codigos_query.filter(
            Q(cod_cierre__icontains=filtro_cod) |
            Q(desc_cod_cierre__icontains=filtro_cod)
        )

    if filtro_app_id:
        # Filtra por el ID exacto de la aplicación
        codigos_query = codigos_query.filter(aplicacion_id=filtro_app_id)

    # --- FIN DE LA CORRECCIÓN ---

    # Obtener todas las aplicaciones para poblar el menú desplegable del filtro
    aplicaciones_para_filtro = Aplicacion.objects.all().order_by('nombre_aplicacion')

    context = {
        'lista_de_codigos': codigos_query,           # <-- Se pasa la lista ya filtrada
        'total_registros': total_registros_db,       # <-- Se pasa el conteo total REAL
        'aplicaciones': aplicaciones_para_filtro,
        'filtros_aplicados': {
            'cod_cierre': filtro_cod,
            'aplicacion': int(filtro_app_id) if filtro_app_id else None,
        }
    }
    return render(request, 'gestion/cod_cierre.html', context)


@login_required
@no_cache
def registrar_cod_cierre_view(request):
    """
    Gestiona el registro de un nuevo código de cierre.
    """
    if request.method == 'POST':
        # 1. Obtener datos del formulario
        id_aplicacion = request.POST.get('aplicacion')
        cod_cierre = request.POST.get('cod_cierre')
        desc_cod_cierre = request.POST.get('desc_cod_cierre')
        causa_cierre = request.POST.get('causa_cierre')

        # 2. Validar que los campos no estén vacíos
        if not all([id_aplicacion, cod_cierre, desc_cod_cierre, causa_cierre]):
            logger.warning(
                f"Usuario '{request.user}' intentó registrar un código de cierre con campos vacíos. Datos: cod_cierre='{cod_cierre}'")
            messages.error(
                request, 'Error: Todos los campos marcados con (*) son obligatorios.')
            # Si hay error, volvemos a cargar el formulario con la lista de apps
            todas_las_aplicaciones = Aplicacion.objects.all()
            return render(request, 'gestion/registrar_cod_cierre.html', {'todas_las_aplicaciones': todas_las_aplicaciones})

        try:
            # 3. Obtener la instancia de la aplicación y crear el nuevo código
            aplicacion_obj = Aplicacion.objects.get(pk=id_aplicacion)
            nuevo_codigo = CodigoCierre(aplicacion=aplicacion_obj, cod_cierre=cod_cierre,
                                        desc_cod_cierre=desc_cod_cierre, causa_cierre=causa_cierre)
            nuevo_codigo.save()

            logger.info(
                f"Usuario '{request.user}' registró el nuevo código de cierre '{cod_cierre}'.")
            messages.success(
                request, f'¡El código de cierre "{cod_cierre}" ha sido registrado con éxito!')
            return redirect('gestion:codigos_cierre')

        except Exception as e:
            logger.error(
                f"Error al registrar código de cierre por '{request.user}': {e}", exc_info=True)
            messages.error(request, f'Ocurrió un error inesperado: {e}')
            return redirect('gestion:registrar_cod_cierre')

    else:  # Método GET: solo muestra el formulario
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para registrar un nuevo código de cierre.")
        todas_las_aplicaciones = Aplicacion.objects.all()
        context = {'todas_las_aplicaciones': todas_las_aplicaciones}
        return render(request, 'gestion/registrar_cod_cierre.html', context)


@login_required
@no_cache
def eliminar_cod_cierre_view(request, pk):
    """
    Elimina un código de cierre específico.
    """
    # Solo se permite el método POST para esta operación por seguridad
    if request.method == 'POST':
        try:
            # Buscamos el código por su clave primaria (pk)
            codigo_a_eliminar = CodigoCierre.objects.get(pk=pk)
            nombre_codigo = codigo_a_eliminar.cod_cierre
            codigo_a_eliminar.delete()
            logger.warning(
                f"El usuario '{request.user}' ha eliminado el código de cierre '{nombre_codigo}' (ID: {pk}).")
            messages.success(
                request, f'El código de cierre "{nombre_codigo}" ha sido eliminado correctamente.')
        except CodigoCierre.DoesNotExist:
            logger.error(
                f"Usuario '{request.user}' intentó eliminar un código de cierre inexistente con ID: {pk}.")
            messages.error(
                request, 'El código de cierre que intentas eliminar no existe.')
        except Exception as e:
            logger.error(
                f"Error al eliminar el código de cierre con ID {pk} por el usuario '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al eliminar el código de cierre: {e}')
    # Redirigimos siempre a la lista de códigos de cierre
    return redirect('gestion:codigos_cierre')


@login_required
@no_cache
def editar_cod_cierre_view(request, pk):
    """
    Gestiona la edición de un código de cierre existente.
    """
    try:
        codigo_a_editar = CodigoCierre.objects.get(pk=pk)
    except CodigoCierre.DoesNotExist:
        logger.error(
            f"Usuario '{request.user}' intentó editar un código de cierre inexistente con ID: {pk}.")
        messages.error(
            request, 'El código de cierre que intentas editar no existe.')
        return redirect('gestion:codigos_cierre')

    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            id_aplicacion = request.POST.get('aplicacion')
            cod_cierre = request.POST.get('cod_cierre')
            desc_cod_cierre = request.POST.get('desc_cod_cierre')
            causa_cierre = request.POST.get('causa_cierre')

            # Actualizar los campos del objeto
            codigo_a_editar.aplicacion = Aplicacion.objects.get(
                pk=id_aplicacion)
            codigo_a_editar.cod_cierre = cod_cierre
            codigo_a_editar.desc_cod_cierre = desc_cod_cierre
            codigo_a_editar.causa_cierre = causa_cierre
            codigo_a_editar.save()

            logger.info(
                f"El usuario '{request.user}' ha actualizado el código de cierre '{cod_cierre}' (ID: {pk}).")
            messages.success(
                request, f'El código de cierre "{cod_cierre}" ha sido actualizado correctamente.')
            return redirect('gestion:codigos_cierre')

        except Exception as e:
            logger.error(
                f"Error al actualizar código de cierre por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al actualizar el código de cierre: {e}')
            return redirect('gestion:editar_cod_cierre', pk=pk)

    else:  # Método GET
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar el código de cierre ID: {pk}.")
        context = {
            # Pasamos la instancia para pre-rellenar el form
            'codigo_cierre': codigo_a_editar,
            'todas_las_aplicaciones': Aplicacion.objects.all()
        }
        return render(request, 'gestion/registrar_cod_cierre.html', context)


# gestion/views/cod_cierre.py

@login_required
@no_cache
def carga_masiva_cod_cierre_view(request):
    """
    Gestiona la carga masiva de códigos de cierre desde un archivo CSV,
    validando duplicados por clave compuesta y registrando un resumen detallado.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha iniciado una carga masiva de códigos de cierre.")
        csv_file = request.FILES.get('csv_file')
        context = {}

        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(
                request, 'Por favor, seleccione un archivo CSV válido.')
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

        try:
            # Decodificación del archivo
            try:
                decoded_file = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                csv_file.seek(0)
                decoded_file = csv_file.read().decode('latin-1')

            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter=';')
            all_rows = list(reader)
            total_records_in_file = len(all_rows)

            # --- NUEVO: VALIDACIÓN DE DUPLICADOS POR CLAVE COMPUESTA ---
            seen_keys = set()
            duplicates_found = []
            for line_number, row in enumerate(all_rows, start=2):
                id_val = row.get('idCodCierre', '').strip()
                cod_val = row.get('cod_cierre', '').strip()

                if not id_val or not cod_val:
                    continue  # No se puede validar una clave incompleta

                composite_key = (id_val, cod_val)
                if composite_key in seen_keys:
                    duplicates_found.append({
                        'line': line_number,
                        'id': id_val,
                        'cod': cod_val
                    })
                else:
                    seen_keys.add(composite_key)

            if duplicates_found:
                error_msg = "El archivo contiene combinaciones de 'idCodCierre' y 'cod_cierre' duplicadas y no pudo ser procesado."
                logger.error(
                    f"{error_msg} Usuario: '{request.user}'. Duplicados: {duplicates_found}")
                messages.error(request, error_msg +
                               " Revisa los detalles a continuación.")
                context['duplicates'] = duplicates_found
                return render(request, 'gestion/carga_masiva_cod_cierre.html', context)
            # --- FIN DE LA VALIDACIÓN DE DUPLICADOS ---

            success_count = 0
            failed_rows = []

            for line_number, row in enumerate(all_rows, start=2):
                try:
                    if not any(field.strip() for field in row.values()):
                        total_records_in_file -= 1
                        continue

                    # ... (lógica de procesamiento de fila que ya tenías)
                    id_cod_cierre_str = row.get('idCodCierre', '').strip()
                    if not id_cod_cierre_str:
                        raise ValueError(
                            "La columna 'idCodCierre' es obligatoria.")
                    id_cod_cierre_pk = int(id_cod_cierre_str)

                    cod_cierre = row.get('cod_cierre', '').strip()
                    id_aplicacion = row.get('id_aplicacion', '').strip()
                    if not all([cod_cierre, id_aplicacion]):
                        raise ValueError(
                            "Las columnas 'cod_cierre' y 'id_aplicacion' son obligatorias.")

                    aplicacion_obj = Aplicacion.objects.get(pk=id_aplicacion)

                    CodigoCierre.objects.update_or_create(
                        id=id_cod_cierre_pk,
                        defaults={
                            'cod_cierre': cod_cierre,
                            'aplicacion': aplicacion_obj,
                            'desc_cod_cierre': row.get('descripcion_cierre', '').strip(),
                            'causa_cierre': row.get('causa_cierre', '').strip()
                        }
                    )
                    success_count += 1

                except Exception as e:
                    failed_rows.append({
                        'line': line_number,
                        'row_data': ';'.join(row.values()),
                        'error': str(e)
                    })

            # --- NUEVO: LOGGING DETALLADO Y MENSAJES A USUARIO ---
            log_summary = f"""
--------------------------------------------------
RESUMEN DE CARGA MASIVA DE CÓDIGOS DE CIERRE
Usuario: {request.user}
Archivo: {csv_file.name}
--------------------------------------------------
Total de filas en el archivo: {total_records_in_file}
Cargados/Actualizados con éxito: {success_count}
Filas con errores: {len(failed_rows)}
--------------------------------------------------"""

            if failed_rows:
                log_summary += "\nDETALLE DE ERRORES:\n"
                for item in failed_rows:
                    log_summary += f"  - Fila {item['line']}: {item['error']} (Datos: {item['row_data']})\n"
                log_summary += "--------------------------------------------------"

            logger.info(log_summary)

            if success_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se procesaron {success_count} registros con éxito.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Revisa los detalles en el log del sistema.')

            context = {
                'failed_rows': failed_rows,
                'stats': {
                    'total': total_records_in_file,
                    'success': success_count,
                    'failed': len(failed_rows)
                }
            }
            return render(request, 'gestion/carga_masiva_cod_cierre.html', context)

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO en carga masiva por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general e inesperado: {e}")
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

    return render(request, 'gestion/carga_masiva_cod_cierre.html')


def obtener_ultimos_codigos_cierre(request, aplicacion_id):
    """
    Esta vista es llamada por AJAX desde el formulario de registro.
    Devuelve los últimos 5 códigos de cierre para una aplicación específica en formato JSON.
    """
    try:
        # Hacemos la consulta a la base de datos:
        # 1. Filtramos por el id de la aplicación.
        # 2. Ordenamos por id en orden descendente para obtener los más recientes.
        # 3. Limitamos el resultado a 5.
        codigos = CodigoCierre.objects.filter(
            aplicacion_id=aplicacion_id).order_by('-id')[:5]

        # Convertimos el queryset a una lista de diccionarios que se puede convertir a JSON.
        data = list(codigos.values('cod_cierre', 'desc_cod_cierre'))

        # Devolvemos los datos en una respuesta JSON.
        return JsonResponse({'codigos': data})

    except Exception as e:
        # En caso de cualquier error, devolvemos una respuesta de error.
        logger.error(
            f"Error en vista AJAX 'obtener_ultimos_codigos_cierre' para app_id {aplicacion_id}: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
