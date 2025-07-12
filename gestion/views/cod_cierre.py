# gestion/views/cod_cierre.py

import csv
import io
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils import no_cache, logger
from ..models import CodigoCierre, Aplicacion


@login_required
@no_cache
def codigos_cierre_view(request):
    """Muestra la lista de códigos de cierre."""
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de códigos de cierre.")
    codigos = CodigoCierre.objects.select_related('aplicacion').all()
    total_registros = codigos.count()
    context = {
        'lista_de_codigos': codigos,
        'total_registros': total_registros,
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


@login_required
@no_cache
def carga_masiva_cod_cierre_view(request):
    """
    Gestiona la carga masiva de códigos de cierre desde un archivo CSV.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha iniciado una carga masiva de códigos de cierre.")
        csv_file = request.FILES.get('csv_file')

        if not csv_file or not csv_file.name.endswith('.csv'):
            logger.warning(
                f"Intento de carga masiva de códigos de cierre por '{request.user}' con archivo no válido.")
            messages.error(
                request, 'Por favor, seleccione un archivo CSV válido.')
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

        success_count = 0
        failed_rows = []
        # Contador para el total de registros no vacíos en el archivo
        total_records_in_file = 0

        try:
            # Intentar decodificar como UTF-8, si falla, usar latin-1
            try:
                decoded_file = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                csv_file.seek(0)
                decoded_file = csv_file.read().decode('latin-1')

            io_string = io.StringIO(decoded_file)
            # Usar DictReader para leer por nombre de columna y especificar el delimitador
            reader = csv.DictReader(io_string, delimiter=';')

            for line_number, row in enumerate(reader, start=2):
                try:
                    # Omitir filas donde todos los valores están vacíos
                    if not any(field.strip() for field in row.values()):
                        continue

                    # Incrementar el contador de registros encontrados para procesar
                    total_records_in_file += 1

                    # 1. Extraer y validar el ID del código de cierre (clave primaria)
                    id_cod_cierre_str = row.get('idCodCierre', '').strip()
                    if not id_cod_cierre_str:
                        raise ValueError(
                            "La columna 'idCodCierre' es obligatoria y no puede estar vacía.")
                    try:
                        id_cod_cierre_pk = int(id_cod_cierre_str)
                    except ValueError:
                        raise ValueError(
                            f"El 'idCodCierre' ('{id_cod_cierre_str}') no es un número válido.")

                    # 2. Extraer los demás campos usando los nombres de las cabeceras
                    cod_cierre = row.get('cod_cierre', '').strip()
                    desc_cod_cierre = row.get('descripcion_cierre', '').strip()
                    causa_cierre = row.get('causa_cierre', '').strip()
                    id_aplicacion = row.get('id_aplicacion', '').strip()

                    # 3. Validar campos obligatorios
                    if not all([cod_cierre, id_aplicacion]):
                        raise ValueError(
                            "El 'cod_cierre' y el 'id_aplicacion' son obligatorios.")

                    # 4. Obtener la instancia de la aplicación relacionada
                    aplicacion_obj = Aplicacion.objects.get(pk=id_aplicacion)

                    # 5. Usar update_or_create con el ID como clave de búsqueda
                    obj, created = CodigoCierre.objects.update_or_create(
                        id=id_cod_cierre_pk,  # <-- Clave de búsqueda es el ID del CSV
                        defaults={
                            'cod_cierre': cod_cierre,
                            'aplicacion': aplicacion_obj,
                            'desc_cod_cierre': desc_cod_cierre,
                            'causa_cierre': causa_cierre
                        })
                    action = "creado con ID fijo" if created else "actualizado"
                    logger.info(
                        f"Registro ID={id_cod_cierre_pk} ('{cod_cierre}') {action} exitosamente.")
                    success_count += 1

                except Aplicacion.DoesNotExist:
                    error_msg = f"La aplicación con ID '{id_aplicacion}' no existe."
                    logger.warning(
                        f"Error en línea {line_number} de carga masiva: {error_msg}. Datos: {row}")
                    failed_rows.append({'line': line_number, 'row_data': ';'.join(
                        map(str, row.values())), 'error': error_msg})
                except Exception as e:
                    error_message = f"Dato problemático: {row}. Error: {e}"
                    logger.error(
                        f"Error en la línea {line_number} del CSV. {error_message}", exc_info=True)
                    failed_rows.append(
                        {'line': line_number, 'row_data': ';'.join(map(str, row.values())), 'error': str(e)})

            # --- INICIO DE CAMBIOS: Mensajes de resumen estadístico ---
            failed_count = len(failed_rows)

            if total_records_in_file > 0:
                summary_message = (
                    f"Proceso de carga finalizado. "
                    f"Registros encontrados: {total_records_in_file}. "
                    f"Cargados/Actualizados: {success_count}. "
                    f"No cargados: {failed_count}."
                )
                if failed_count > 0:
                    messages.warning(request, summary_message)
                else:
                    messages.success(request, summary_message)
            else:
                messages.info(
                    request, "El archivo CSV está vacío o no contiene datos para procesar.")
            # --- FIN DE CAMBIOS ---
        except Exception as e:
            logger.critical(
                f"Error CRÍTICO durante la carga masiva de códigos de cierre por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general al procesar el archivo: {e}")
        return render(request, 'gestion/carga_masiva_cod_cierre.html', {'failed_rows': failed_rows})

    logger.info(
        f"Usuario '{request.user}' accedió a la página de carga masiva de códigos de cierre.")
    return render(request, 'gestion/carga_masiva_cod_cierre.html')
