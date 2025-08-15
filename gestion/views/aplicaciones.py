# gestion/views/aplicaciones.py

import csv
import io
from ..models import Aplicacion, Bloque, Criticidad, Estado
from .utils import no_cache
from django.contrib import messages, auth
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import Aplicacion, Bloque, Criticidad, Estado


@login_required
@no_cache
def aplicaciones_view(request):
    """
    Renderiza la página principal del mantenedor de aplicaciones.

    Esta vista se encarga de:
    1.  Obtener y mostrar una lista de todas las aplicaciones.
    2.  Procesar y aplicar los filtros de búsqueda enviados por el usuario
        a través de una petición GET.
    3.  Poblar los menús desplegables (<select>) del formulario de filtros.
    4.  Pasar los datos filtrados y la información necesaria a la plantilla.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Una respuesta HTTP que renderiza la plantilla
                      'gestion/aplicaciones.html' con el contexto necesario.

    Context:
        'lista_de_aplicaciones' (QuerySet<Aplicacion>): El conjunto de aplicaciones
            resultante después de aplicar los filtros.
        'total_registros' (int): El número total de aplicaciones existentes en la BD.
        'todos_los_bloques' (QuerySet<Bloque>): Lista de todos los bloques para el filtro.
        'todas_las_criticidades' (QuerySet<Criticidad>): Lista de todas las
            criticidades para el filtro.
        'todos_los_estados' (QuerySet<Estado>): Lista de todos los estados de tipo
            'Aplicacion' para el filtro.
    """
    # --- 1. Inicio y Registro de Acceso ---
    logger.info(
        f"El usuario '{request.user}' ha accedido a la vista de aplicaciones.")

    # --- 2. Queryset Base ---
    # Se utiliza select_related para optimizar la consulta, precargando los datos
    # de las tablas relacionadas (Bloque, Criticidad, Estado) en una sola consulta SQL.
    aplicaciones_qs = Aplicacion.objects.select_related(
        'bloque', 'criticidad', 'estado').all()

    # --- 3. Procesamiento de Filtros ---
    # Se recogen los parámetros de la URL. Si no existen, .get() devuelve None.
    filtro_nombre = request.GET.get('nombre_app')
    filtro_codigo = request.GET.get('codigo_app')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_criticidad_id = request.GET.get('criticidad')
    filtro_estado_id = request.GET.get('estado')

    # Lista para registrar qué filtros se están usando en esta petición.
    filtros_aplicados = []

    if filtro_nombre:
        aplicaciones_qs = aplicaciones_qs.filter(
            nombre_aplicacion__icontains=filtro_nombre)
        filtros_aplicados.append(f"nombre='{filtro_nombre}'")

    if filtro_codigo:
        aplicaciones_qs = aplicaciones_qs.filter(
            cod_aplicacion__icontains=filtro_codigo)
        filtros_aplicados.append(f"código='{filtro_codigo}'")

    if filtro_bloque_id and filtro_bloque_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(bloque_id=filtro_bloque_id)
        filtros_aplicados.append(f"bloque_id='{filtro_bloque_id}'")

    if filtro_criticidad_id and filtro_criticidad_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(
            criticidad_id=filtro_criticidad_id)
        filtros_aplicados.append(f"criticidad_id='{filtro_criticidad_id}'")

    if filtro_estado_id and filtro_estado_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(estado_id=filtro_estado_id)
        filtros_aplicados.append(f"estado_id='{filtro_estado_id}'")

    # Si se aplicó al menos un filtro, se registra en el log.
    if filtros_aplicados:
        logger.info(
            f"Búsqueda de aplicaciones con filtros: {', '.join(filtros_aplicados)}.")

    # Se registra cuántos resultados se encontraron con los filtros actuales.
    num_resultados = aplicaciones_qs.count()
    logger.info(f"La consulta ha devuelto {num_resultados} aplicaciones.")

    # --- 4. Preparación del Contexto para la Plantilla ---
    # Se obtienen los datos necesarios para poblar los menús desplegables de los filtros.
    todos_los_bloques = Bloque.objects.all().order_by('desc_bloque')
    todas_las_criticidades = Criticidad.objects.all().order_by('desc_criticidad')
    todos_los_estados = Estado.objects.filter(
        uso_estado=Estado.UsoChoices.APLICACION).order_by('desc_estado')

    # Se obtiene el conteo total de aplicaciones en el sistema para mostrarlo como estadística.
    total_registros = Aplicacion.objects.count()

    context = {
        'lista_de_aplicaciones': aplicaciones_qs,
        'total_registros': total_registros,
        'todos_los_bloques': todos_los_bloques,
        'todas_las_criticidades': todas_las_criticidades,
        'todos_los_estados': todos_los_estados,
    }

    # --- 5. Renderizado Final ---
    return render(request, 'gestion/aplicaciones.html', context)


@no_cache
@login_required
def registrar_aplicacion_view(request):
    """
    Gestiona la visualización del formulario y el registro de una nueva aplicación.

    Esta vista tiene dos comportamientos dependiendo del método HTTP:
    - GET: Muestra un formulario vacío para que el usuario ingrese los datos de
      una nueva aplicación. Carga las listas de bloques, criticidades y estados
      necesarias para los campos de selección del formulario.
    - POST: Procesa los datos enviados desde el formulario. Valida que los campos
      requeridos estén presentes, crea una nueva instancia del modelo `Aplicacion`,
      la guarda en la base de datos y redirige al usuario a la lista de aplicaciones.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse:
            - Si el método es GET, renderiza la plantilla 'gestion/registrar_aplicacion.html'.
            - Si el método es POST, redirige a la vista 'gestion:aplicaciones' tras
              un registro exitoso, o de vuelta al formulario en caso de error.

    Context (solo en GET):
        'todos_los_bloques' (QuerySet<Bloque>): Lista de todos los bloques.
        'todas_las_criticidades' (QuerySet<Criticidad>): Lista de todas las criticidades.
        'todos_los_estados' (QuerySet<Estado>): Lista de estados filtrados por uso 'Aplicacion'.
    """
    # --- Escenario 1: El usuario envía datos para crear un registro (POST) ---
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de registro de aplicación.")

        # Obtenemos los datos del formulario enviado
        cod_aplicacion = request.POST.get('cod_aplicacion')
        nombre_aplicacion = request.POST.get('nombre_aplicacion')
        id_bloque = request.POST.get('bloque')
        id_criticidad = request.POST.get('criticidad')
        id_estado = request.POST.get('estado')
        desc_aplicacion = request.POST.get('desc_aplicacion')

        # Validación simple para campos obligatorios.
        if not all([cod_aplicacion, nombre_aplicacion, id_bloque, id_criticidad, id_estado]):
            logger.warning(
                f"Intento de registro fallido por el usuario '{request.user}' debido a campos obligatorios faltantes."
            )
            messages.error(
                request, 'Error: Todos los campos marcados con (*) son obligatorios.')
            # Redirigimos de nuevo al formulario para que el usuario corrija los errores.
            return redirect('gestion:registrar_aplicacion')

        try:
            # Obtenemos las instancias de los modelos relacionados.
            # Esto puede lanzar una excepción si un ID no existe (ej: .get() no encuentra el objeto).
            bloque = Bloque.objects.get(pk=id_bloque)
            criticidad = Criticidad.objects.get(pk=id_criticidad)
            estado = Estado.objects.get(pk=id_estado)

            # Creamos la nueva instancia del modelo Aplicacion pero aún no la guardamos.
            nueva_aplicacion = Aplicacion(
                cod_aplicacion=cod_aplicacion,
                nombre_aplicacion=nombre_aplicacion,
                bloque=bloque,
                criticidad=criticidad,
                estado=estado,
                desc_aplicacion=desc_aplicacion
            )
            # Guardamos el objeto en la base de datos.
            nueva_aplicacion.save()

            logger.info(
                f"El usuario '{request.user}' ha registrado con éxito la aplicación '{nombre_aplicacion}' (ID: {nueva_aplicacion.id})."
            )
            messages.success(
                request, f'¡La aplicación "{nombre_aplicacion}" ha sido registrada con éxito!')

            return redirect('gestion:aplicaciones')

        except Exception as e:
            # Si ocurre cualquier error durante la obtención de objetos o al guardar...
            logger.error(
                f"Error crítico al guardar la aplicación por el usuario '{request.user}'. Error: {e}",
                # exc_info=True registra el traceback completo del error.
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error inesperado al guardar la aplicación: {e}')
            return redirect('gestion:registrar_aplicacion')

    # --- Escenario 2: El usuario solicita ver el formulario (GET) ---
    else:
        logger.info(
            f"El usuario '{request.user}' está viendo el formulario para registrar una nueva aplicación.")
        try:
            # Obtenemos los datos para poblar los menús desplegables del formulario.
            todos_los_bloques = Bloque.objects.all().order_by('desc_bloque')
            todas_las_criticidades = Criticidad.objects.all().order_by('desc_criticidad')
            todos_los_estados = Estado.objects.filter(
                uso_estado=Estado.UsoChoices.APLICACION).order_by('desc_estado')

            context = {
                'todos_los_bloques': todos_los_bloques,
                'todas_las_criticidades': todas_las_criticidades,
                'todos_los_estados': todos_los_estados,
            }
            return render(request, 'gestion/registrar_aplicacion.html', context)

        except Exception as e:
            # Si hay un error al consultar los datos para el formulario (ej. BD no disponible).
            logger.error(
                f"No se pudo cargar la data para el formulario de registro. Error: {e}",
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al cargar los datos para el formulario: {e}')
            return redirect('gestion:aplicaciones')


@login_required
@no_cache
def carga_masiva_view(request):
    """
    Gestiona la carga y procesamiento masivo de aplicaciones desde un archivo CSV.

    Esta vista maneja dos escenarios:
    - GET: Muestra la página con el formulario para subir el archivo.
    - POST: Procesa el archivo CSV subido. El proceso incluye:
        1.  Validación del archivo (debe ser .csv).
        2.  Lectura y decodificación del contenido (soporta UTF-8 y Latin-1).
        3.  Pre-validación para detectar claves duplicadas ('id_aplicacion', 'id_modulo')
            dentro del propio archivo, deteniendo el proceso si se encuentran.
        4.  Procesamiento fila por fila del CSV.
        5.  Mapeo de valores de texto (ej. 'alta') a registros de la BD (ej. Criticidad 'critica').
        6.  Uso de `get_or_create` para crear nuevas aplicaciones o identificar las existentes.
        7.  Registro detallado de éxitos, omisiones y errores por fila.
        8.  Generación de un resumen final en los logs y en la interfaz de usuario.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/carga_masiva_aplicativo.html'
                      con el contexto del resultado de la carga.

    Context (solo en POST):
        'duplicates' (list, opcional): Lista de duplicados encontrados en la pre-validación.
        'failed_rows' (list, opcional): Lista de filas que fallaron durante el procesamiento.
        'stats' (dict, opcional): Diccionario con estadísticas de la carga (total, éxitos, etc.).
    """
    logger.info(
        f"El usuario '{request.user}' está viendo el formulario de carga masiva.")
    # --- 1. Procesamiento de la Petición POST ---
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha iniciado una carga masiva de aplicaciones.")
        csv_file = request.FILES.get('csv_file')
        context = {}

        # Validar que se haya subido un archivo y que sea de tipo .csv
        if not csv_file or not csv_file.name.endswith('.csv'):
            logger.warning(
                f"Intento de carga masiva por '{request.user}' fallido: no se seleccionó un archivo CSV válido."
            )
            messages.error(
                request, 'Por favor, seleccione un archivo CSV válido.')
            return render(request, 'gestion/carga_masiva_aplicativo.html')

        try:
            # --- 2. Lectura y Decodificación del Archivo ---
            logger.info(f"Leyendo el archivo '{csv_file.name}'...")
            try:
                decoded_file = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(
                    f"El archivo '{csv_file.name}' no es UTF-8. Intentando con Latin-1.")
                csv_file.seek(0)
                decoded_file = csv_file.read().decode('latin-1')

            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter=';')
            all_rows = list(reader)
            total_records_in_file = len(all_rows)
            logger.info(
                f"Se leyeron {total_records_in_file} filas del archivo.")

            # --- 3. Pre-validación de Duplicados en el Archivo ---
            logger.info(
                "Iniciando pre-validación de duplicados en el archivo...")
            seen_keys, duplicates_found = set(), []
            for line_number, row in enumerate(all_rows, start=2):
                composite_key = (row.get('id_aplicacion', '').strip(), row.get(
                    'id_modulo', '').strip())
                if all(composite_key):
                    if composite_key in seen_keys:
                        duplicates_found.append(
                            {'line': line_number, 'id': composite_key[0], 'cod': composite_key[1]})
                    else:
                        seen_keys.add(composite_key)

            if duplicates_found:
                error_msg = "El archivo contiene claves ('id_aplicacion', 'id_modulo') duplicadas y no pudo ser procesado."
                logger.error(
                    f"{error_msg} Usuario: '{request.user}'. Duplicados: {duplicates_found}")
                messages.error(request, error_msg +
                               " Revisa los detalles a continuación.")
                context['duplicates'] = duplicates_found
                return render(request, 'gestion/carga_masiva_aplicativo.html', context)
            logger.info(
                "Pre-validación completada. No se encontraron duplicados internos.")

            # --- 4. Mapeo de Datos y Procesamiento por Filas ---
            criticidad_map = {'alta': 'critica', 'critica': 'critica', 'crítica': 'critica', 'media': 'no critica',
                              'no critica': 'no critica', 'baja': 'sin criticidad', 'sin criticidad': 'sin criticidad', 'no crítica': 'no critica'}
            estado_map = {'dev': 'Construccion', 'construccion': 'Construccion', 'en construcción': 'Construccion', 'prod': 'Produccion', 'produccion': 'Produccion',
                          'en producción': 'Produccion', 'en revisión': 'Pendiente', 'desuso': 'Deshuso', 'pendiente': 'Pendiente', 'resuelto': 'Resuelto', 'cerrado': 'Cerrado'}
            bloque_map = {'b1': 'BLOQUE 1', 'bloque 1': 'BLOQUE 1', 'b2': 'BLOQUE 2', 'bloque 2': 'BLOQUE 2', 'b3': 'BLOQUE 3',
                          'bloque 3': 'BLOQUE 3', 'b4': 'BLOQUE 4', 'bloque 4': 'BLOQUE 4', 'ninguno': 'Sin bloque', 'sin bloque': 'Sin bloque'}

            success_count, failed_rows, skipped_count = 0, [], 0

            logger.info("Iniciando procesamiento de cada fila...")
            for line_number, row in enumerate(all_rows, start=2):
                try:
                    if not any(field.strip() for field in row.values()):
                        total_records_in_file -= 1
                        continue

                    id_aplicacion_str = row.get('id_aplicacion', '').strip()
                    if not id_aplicacion_str:
                        raise ValueError(
                            "La columna 'id_aplicacion' es obligatoria.")
                    id_aplicacion_pk = int(id_aplicacion_str)

                    cod_aplicacion = row.get('id_modulo', '').strip()
                    nombre_aplicacion = row.get('nombre_app', '').strip()
                    if not cod_aplicacion or not nombre_aplicacion:
                        raise ValueError(
                            "Las columnas 'id_modulo' y 'nombre_app' son obligatorias.")

                    # Lógica de mapeo y obtención de objetos relacionados
                    criticidad_csv = row.get('criticidad', '').strip().lower()
                    estado_csv = row.get('estado', '').strip().lower()
                    bloque_csv = row.get('bloque', '').strip().lower()

                    criticidad_str = criticidad_map.get(
                        criticidad_csv, row.get('criticidad', '').strip())
                    estado_str = estado_map.get(
                        estado_csv, row.get('estado', '').strip())
                    bloque_str = bloque_map.get(
                        bloque_csv, row.get('bloque', '').strip())

                    bloque_obj = Bloque.objects.get(
                        desc_bloque__iexact=bloque_str) if bloque_str else None
                    criticidad_obj = Criticidad.objects.get(
                        desc_criticidad__iexact=criticidad_str) if criticidad_str else None
                    estado_obj = Estado.objects.get(
                        desc_estado__iexact=estado_str) if estado_str else None

                    # Creación o obtención del registro
                    obj, created = Aplicacion.objects.get_or_create(
                        id=id_aplicacion_pk,
                        defaults={
                            'cod_aplicacion': cod_aplicacion,
                            'nombre_aplicacion': nombre_aplicacion,
                            'bloque': bloque_obj,
                            'criticidad': criticidad_obj,
                            'estado': estado_obj,
                            'desc_aplicacion': row.get('descripcion', '').strip(),
                        }
                    )

                    if created:
                        success_count += 1
                        logger.info(
                            f"Fila {line_number}: APLICACIÓN CREADA (ID: {id_aplicacion_pk}, Código: '{cod_aplicacion}').")
                    else:
                        skipped_count += 1
                        logger.info(
                            f"Fila {line_number}: APLICACIÓN OMITIDA (ID: {id_aplicacion_pk} ya existe).")

                except Exception as e:
                    # Captura de error por fila para no detener todo el proceso
                    logger.error(
                        f"Error procesando la fila {line_number}. Error: {e} | Datos: {row}",
                        exc_info=True
                    )
                    failed_rows.append(
                        {'line': line_number, 'row_data': ';'.join(row.values()), 'error': str(e)})

            # --- 5. Generación de Resumen y Respuesta ---
            logger.info(
                "Procesamiento de filas finalizado. Generando resumen.")
            log_summary = (
                f"\n--------------------------------------------------"
                f"\nRESUMEN DE CARGA MASIVA DE APLICACIONES"
                f"\nUsuario: {request.user}"
                f"\nArchivo: {csv_file.name}"
                f"\n--------------------------------------------------"
                f"\nTotal de filas leídas: {total_records_in_file}"
                f"\nAplicaciones nuevas creadas: {success_count}"
                f"\nAplicaciones omitidas (ya existían): {skipped_count}"
                f"\nFilas con errores: {len(failed_rows)}"
                f"\n--------------------------------------------------"
            )

            if failed_rows:
                log_summary += "\nDETALLE DE ERRORES:\n"
                for item in failed_rows:
                    log_summary += f"  - Fila {item['line']}: {item['error']} (Datos: {item['row_data']})\n"
                log_summary += "--------------------------------------------------"

            logger.info(log_summary)

            if success_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se crearon {success_count} aplicaciones nuevas.')
            if skipped_count > 0:
                messages.info(
                    request, f'Se omitieron {skipped_count} aplicaciones que ya existían.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Revisa los detalles en el log del sistema.')

            context = {'failed_rows': failed_rows, 'stats': {'total': total_records_in_file,
                                                             'skipped': skipped_count, 'success': success_count, 'failed': len(failed_rows)}}
            return render(request, 'gestion/carga_masiva_aplicativo.html', context)

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO en carga masiva por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general e inesperado: {e}")
            return render(request, 'gestion/carga_masiva_aplicativo.html')

    # --- Respuesta para Peticiones GET ---
    return render(request, 'gestion/carga_masiva_aplicativo.html')


@login_required
@no_cache
def eliminar_aplicacion_view(request, pk):
    """
    Gestiona la eliminación de una aplicación específica.

    Esta vista está protegida para aceptar únicamente peticiones POST,
    como medida de seguridad para prevenir eliminaciones accidentales
    a través de enlaces (peticiones GET).

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria (ID) de la aplicación a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la vista 'gestion:aplicaciones'
                      después de la operación.
    """
    # Se valida que la petición sea POST para proceder con la eliminación.
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de eliminación para la aplicación con ID: {pk}.")
        try:
            # Se busca la aplicación por su clave primaria.
            aplicacion_a_eliminar = Aplicacion.objects.get(pk=pk)
            nombre_app = aplicacion_a_eliminar.nombre_aplicacion

            # Se elimina el objeto de la base de datos.
            aplicacion_a_eliminar.delete()

            # Se registra la eliminación como una advertencia (WARNING) para que sea
            # fácil de localizar en los logs, ya que es una acción destructiva.
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO la aplicación '{nombre_app}' (ID: {pk})."
            )
            messages.success(
                request, f'La aplicación "{nombre_app}" ha sido eliminada correctamente.')

        except Aplicacion.DoesNotExist:
            # Este error ocurre si se intenta eliminar una aplicación que ya no existe.
            logger.warning(
                f"Intento de eliminación fallido: La aplicación con ID {pk} no existe. Solicitado por '{request.user}'."
            )
            messages.error(
                request, 'La aplicación que intentas eliminar no existe.')

        except Exception as e:
            # Captura cualquier otro error inesperado durante la eliminación.
            logger.error(
                f"Error crítico al eliminar la aplicación ID {pk} por el usuario '{request.user}'. Error: {e}",
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al eliminar la aplicación: {e}')

    # Si la petición no es POST, o después de la operación, se redirige.
    return redirect('gestion:aplicaciones')


@login_required
@no_cache
def editar_aplicacion_view(request, pk):
    """
    Gestiona la visualización y actualización de una aplicación existente.

    - GET: Busca la aplicación por su 'pk', carga sus datos y los de las
      tablas relacionadas (Bloque, etc.) y renderiza el formulario de registro
      pre-poblado con esta información.
    - POST: Procesa los datos enviados. Actualiza los campos de la aplicación,
      guarda los cambios en la BD y redirige a la lista de aplicaciones.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria (ID) de la aplicación a editar.

    Returns:
        HttpResponse:
            - Si no se encuentra la aplicación, redirige a 'gestion:aplicaciones'.
            - Si el método es GET, renderiza la plantilla 'gestion/registrar_aplicacion.html'.
            - Si el método es POST, redirige a 'gestion:aplicaciones' (éxito) o a la
              misma página de edición (error).

    Context (solo en GET):
        'aplicacion' (Aplicacion): La instancia de la aplicación que se está editando.
        'todos_los_bloques' (QuerySet<Bloque>): Lista de todos los bloques.
        # ... y otras listas para los selectores.
    """
    # --- 1. Obtención del Objeto a Editar ---
    try:
        aplicacion_a_editar = Aplicacion.objects.get(pk=pk)
        logger.info(
            f"Usuario '{request.user}' ha accedido al formulario de edición para la aplicación '{aplicacion_a_editar.nombre_aplicacion}' (ID: {pk}).")
    except Aplicacion.DoesNotExist:
        logger.warning(
            f"Intento de acceso a una aplicación no existente (ID: {pk}) por el usuario '{request.user}'.")
        messages.error(request, 'La aplicación que intentas editar no existe.')
        return redirect('gestion:aplicaciones')

    # --- 2. Procesamiento de la Petición POST (Actualización) ---
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha enviado datos para actualizar la aplicación ID: {pk}.")
        try:
            # Se actualizan los campos del objeto con los datos del formulario.
            aplicacion_a_editar.cod_aplicacion = request.POST.get(
                'cod_aplicacion')
            aplicacion_a_editar.nombre_aplicacion = request.POST.get(
                'nombre_aplicacion')
            aplicacion_a_editar.desc_aplicacion = request.POST.get(
                'desc_aplicacion')
            aplicacion_a_editar.bloque = Bloque.objects.get(
                pk=request.POST.get('bloque'))
            aplicacion_a_editar.criticidad = Criticidad.objects.get(
                pk=request.POST.get('criticidad'))
            aplicacion_a_editar.estado = Estado.objects.get(
                pk=request.POST.get('estado'))

            # Se guardan todos los cambios en la base de datos en una sola transacción.
            aplicacion_a_editar.save()

            nombre_actualizado = aplicacion_a_editar.nombre_aplicacion
            logger.info(
                f"El usuario '{request.user}' ha actualizado con éxito la aplicación '{nombre_actualizado}' (ID: {pk}).")
            messages.success(
                request, f'La aplicación "{nombre_actualizado}" ha sido actualizada correctamente.')
            return redirect('gestion:aplicaciones')

        except Exception as e:
            logger.error(
                f"Error crítico al actualizar la aplicación ID {pk} por '{request.user}'. Error: {e}",
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al actualizar la aplicación: {e}')
            return redirect('gestion:editar_aplicacion', pk=pk)

    # --- 3. Respuesta a la Petición GET (Mostrar Formulario) ---
    else:
        try:
            context = {
                'aplicacion': aplicacion_a_editar,
                'todos_los_bloques': Bloque.objects.all(),
                'todas_las_criticidades': Criticidad.objects.all(),
                'todos_los_estados': Estado.objects.filter(uso_estado=Estado.UsoChoices.APLICACION),
            }
            # Se reutiliza la misma plantilla de registro para la edición.
            return render(request, 'gestion/registrar_aplicacion.html', context)
        except Exception as e:
            logger.error(
                f"No se pudo cargar la data para el formulario de edición (ID: {pk}). Error: {e}",
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al cargar los datos para el formulario: {e}')
            return redirect('gestion:aplicaciones')
