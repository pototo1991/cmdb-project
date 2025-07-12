# gestion/views/aplicaciones.py

import csv
import io
from ..models import Aplicacion, Bloque, Criticidad, Estado
from .utils import no_cache
from django.contrib import messages, auth
from django.shortcuts import render, redirect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import Aplicacion


@login_required
@no_cache
def aplicaciones_view(request):
    """Muestra la lista de aplicaciones."""
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de aplicaciones.")
    aplicaciones = Aplicacion.objects.select_related(
        'bloque', 'criticidad', 'estado').all()
    # 1. Contamos el total de registros.
    total_registros = aplicaciones.count()

    # 2. Añadimos el total al contexto que se envía a la plantilla.
    context = {
        'lista_de_aplicaciones': aplicaciones,
        'total_registros': total_registros,
    }

    return render(request, 'gestion/aplicaciones.html', context)


# Asumo que tu decorador está en gestion/views/utils.py
# Importa los modelos necesarios desde tu archivo models.py


@no_cache
@login_required
def registrar_aplicacion_view(request):
    """
    Gestiona el registro de una nueva aplicación.
    """
    # Escenario 1: El usuario envía el formulario (método POST)
    if request.method == 'POST':
        # Obtenemos los datos del formulario enviado
        cod_aplicacion = request.POST.get('cod_aplicacion')
        nombre_aplicacion = request.POST.get('nombre_aplicacion')
        id_bloque = request.POST.get('bloque')
        id_criticidad = request.POST.get('criticidad')
        id_estado = request.POST.get('estado')
        desc_aplicacion = request.POST.get('desc_aplicacion')

        # Realizamos una validación simple (puedes añadir más si lo necesitas)
        if not all([cod_aplicacion, nombre_aplicacion, id_bloque, id_criticidad, id_estado]):
            messages.error(
                request, 'Error: Todos los campos marcados son obligatorios.')
            # Si hay un error, volvemos a mostrar el formulario
            # (aquí podrías pasar los datos ya ingresados para no perderlos)
            return redirect('gestion:registrar_aplicacion')

        try:
            # Obtenemos las instancias de los modelos relacionados (Bloque, Criticidad, etc.)
            bloque = Bloque.objects.get(pk=id_bloque)
            criticidad = Criticidad.objects.get(pk=id_criticidad)
            estado = Estado.objects.get(pk=id_estado)

            # Creamos la nueva instancia del modelo Aplicacion
            nueva_aplicacion = Aplicacion(
                cod_aplicacion=cod_aplicacion,
                nombre_aplicacion=nombre_aplicacion,
                bloque=bloque,
                criticidad=criticidad,
                estado=estado,
                desc_aplicacion=desc_aplicacion
            )
            # Guardamos el objeto en la base de datos
            nueva_aplicacion.save()

            # Enviamos un mensaje de éxito que se mostrará en la siguiente página
            messages.success(
                request, f'¡La aplicación "{nombre_aplicacion}" ha sido registrada con éxito!')

            # Redirigimos al usuario a la lista de aplicaciones
            return redirect('gestion:aplicaciones')

        except Exception as e:
            messages.error(
                request, f'Ocurrió un error al guardar la aplicación: {e}')
            return redirect('gestion:registrar_aplicacion')

    # Escenario 2: El usuario solo pide ver la página del formulario (método GET)
    else:
        # Obtenemos todos los objetos de los modelos relacionados para poblar los <select> del formulario
        try:
            todos_los_bloques = Bloque.objects.all()
            todas_las_criticidades = Criticidad.objects.all()
            todos_los_estados = Estado.objects.all()

            # Creamos el contexto para pasarlo a la plantilla
            context = {
                'todos_los_bloques': todos_los_bloques,
                'todas_las_criticidades': todas_las_criticidades,
                'todos_los_estados': todos_los_estados,
            }
            return render(request, 'gestion/registrar_aplicacion.html', context)

        except Exception as e:
            messages.error(
                request, f'Ocurrió un error al cargar los datos para el formulario: {e}')
            return redirect('gestion:aplicaciones')


@login_required
@no_cache
def carga_masiva_view(request):
    """
    Gestiona la carga masiva de aplicaciones desde un archivo CSV con mapeo de datos.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha iniciado una carga masiva de aplicaciones.")
        csv_file = request.FILES.get('csv_file')

        if not csv_file or not csv_file.name.endswith('.csv'):
            logger.warning(
                f"Intento de carga masiva por '{request.user}' con un archivo no válido o ausente.")
            messages.error(
                request, 'Por favor, seleccione un archivo CSV válido.')
            return render(request, 'gestion/carga_masiva_aplicativo.html')

        criticidad_map = {
            'alta': 'critica', 'critica': 'critica', 'crítica': 'critica', 'media': 'no critica',
            'no critica': 'no critica', 'baja': 'sin criticidad', 'sin criticidad': 'sin criticidad',
            'no crítica': 'no critica', 'no crítica': 'no critica',  # Añadido por el acento
        }
        estado_map = {
            'dev': 'Construccion', 'construccion': 'Construccion', 'en construcción': 'Construccion', 'prod': 'Produccion',
            'produccion': 'Produccion', 'en producción': 'Produccion', 'en revisión': 'Pendiente', 'desuso': 'Deshuso',
            'pendiente': 'Pendiente', 'resuelto': 'Resuelto', 'cerrado': 'Cerrado',
        }
        bloque_map = {
            'b1': 'BLOQUE 1', 'bloque 1': 'BLOQUE 1', 'b2': 'BLOQUE 2', 'bloque 2': 'BLOQUE 2',
            'b3': 'BLOQUE 3', 'bloque 3': 'BLOQUE 3', 'b4': 'BLOQUE 4', 'bloque 4': 'BLOQUE 4',
            'ninguno': 'Sin bloque', 'sin bloque': 'Sin bloque',
        }

        success_count = 0
        failed_rows = []

        try:
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

                    # 1. Extraer y validar el ID de la aplicación (clave primaria)
                    id_aplicacion_str = row.get('id_aplicacion', '').strip()
                    if not id_aplicacion_str:
                        raise ValueError(
                            "La columna 'id_aplicacion' es obligatoria y no puede estar vacía.")
                    try:
                        id_aplicacion_pk = int(id_aplicacion_str)
                    except ValueError:
                        raise ValueError(
                            f"El 'id_aplicacion' ('{id_aplicacion_str}') no es un número válido.")

                    # 2. Extraer los demás campos usando los nombres de las cabeceras
                    cod_aplicacion = row.get('id_modulo', '').strip()
                    nombre_aplicacion = row.get('nombre_app', '').strip()
                    desc_aplicacion = row.get('descripcion', '').strip()

                    criticidad_csv = row.get('criticidad', '').strip().lower()
                    estado_csv = row.get('estado', '').strip().lower()
                    bloque_csv = row.get('bloque', '').strip().lower()

                    # 3. Mapear y obtener objetos de clave foránea
                    criticidad_str = criticidad_map.get(
                        criticidad_csv, row.get('criticidad', '').strip())
                    estado_str = estado_map.get(
                        estado_csv, row.get('estado', '').strip())
                    bloque_str = bloque_map.get(
                        bloque_csv, row.get('bloque', '').strip())

                    # 4. Validar campos obligatorios (además del ID)
                    if not cod_aplicacion or not nombre_aplicacion:
                        raise ValueError(
                            "Las columnas 'id_modulo' y 'nombre_app' son obligatorias.")

                    # 5. Obtener instancias de los modelos relacionados
                    bloque_obj = Bloque.objects.get(
                        desc_bloque__iexact=bloque_str) if bloque_str else None
                    criticidad_obj = Criticidad.objects.get(
                        desc_criticidad__iexact=criticidad_str) if criticidad_str else None
                    estado_obj = Estado.objects.get(
                        desc_estado__iexact=estado_str) if estado_str else None

                    # 6. Usar update_or_create con el ID como clave de búsqueda
                    obj, created = Aplicacion.objects.update_or_create(
                        id=id_aplicacion_pk,  # <-- Clave de búsqueda es el ID del CSV
                        defaults={
                            'cod_aplicacion': cod_aplicacion,
                            'nombre_aplicacion': nombre_aplicacion,
                            'bloque': bloque_obj,
                            'criticidad': criticidad_obj,
                            'estado': estado_obj,
                            'desc_aplicacion': desc_aplicacion
                        }
                    )
                    action = "creado con ID fijo" if created else "actualizado"
                    logger.info(
                        f"Registro ID={id_aplicacion_pk} ('{cod_aplicacion}') {action} exitosamente.")
                    success_count += 1

                except Exception as e:
                    error_message = f"Dato problemático: {row}. Error: {e}"
                    logger.error(
                        f"Error en la línea {line_number} del CSV. {error_message}", exc_info=True)
                    failed_rows.append({
                        'line': line_number,
                        'row_data': ';'.join(map(str, row.values())),
                        'error': str(e)
                    })

            if success_count > 0:
                messages.success(
                    request, f'{success_count} registros fueron procesados exitosamente.')
            if failed_rows:
                messages.warning(
                    request, f'{len(failed_rows)} registros no pudieron ser procesados. Ver detalles abajo.')

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO durante el proceso de carga masiva. Error: {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general al procesar el archivo: {e}")

        context = {'failed_rows': failed_rows}
        return render(request, 'gestion/carga_masiva_aplicativo.html', context)

    return render(request, 'gestion/carga_masiva_aplicativo.html')


@login_required
@no_cache
def eliminar_aplicacion_view(request, pk):
    """
    Elimina una aplicación específica.
    """
    # Solo se permite el método POST para esta operación
    if request.method == 'POST':
        try:
            # Buscamos la aplicación por su clave primaria (pk)
            aplicacion_a_eliminar = Aplicacion.objects.get(pk=pk)
            nombre_app = aplicacion_a_eliminar.nombre_aplicacion
            aplicacion_a_eliminar.delete()
            logger.warning(
                f"El usuario '{request.user}' ha eliminado la aplicación '{nombre_app}' (ID: {pk}).")
            messages.success(
                request, f'La aplicación "{nombre_app}" ha sido eliminada correctamente.')
        except Aplicacion.DoesNotExist:
            messages.error(
                request, 'La aplicación que intentas eliminar no existe.')
        except Exception as e:
            messages.error(
                request, f'Ocurrió un error al eliminar la aplicación: {e}')
    # Redirigimos siempre a la lista de aplicaciones
    return redirect('gestion:aplicaciones')


@login_required
@no_cache
def editar_aplicacion_view(request, pk):
    """
    Gestiona la edición de una aplicación existente.
    """
    try:
        # Buscamos la aplicación que se va a editar por su Primary Key (pk)
        aplicacion_a_editar = Aplicacion.objects.get(pk=pk)
    except Aplicacion.DoesNotExist:
        messages.error(request, 'La aplicación que intentas editar no existe.')
        return redirect('gestion:aplicaciones')

    if request.method == 'POST':
        # Si el formulario se envía (método POST), procesamos los datos
        try:
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

            aplicacion_a_editar.save()  # Guardamos los cambios en la base de datos

            logger.info(
                f"El usuario '{request.user}' ha actualizado la aplicación '{aplicacion_a_editar.nombre_aplicacion}' (ID: {pk}).")
            messages.success(
                request, f'La aplicación "{aplicacion_a_editar.nombre_aplicacion}" ha sido actualizada correctamente.')
            return redirect('gestion:aplicaciones')

        except Exception as e:
            messages.error(
                request, f'Ocurrió un error al actualizar la aplicación: {e}')
            # Si hay un error, volvemos a la página de edición
            return redirect('gestion:editar_aplicacion', pk=pk)

    else:
        # Si es una petición GET, mostramos el formulario con los datos existentes
        try:
            context = {
                'aplicacion': aplicacion_a_editar,  # Pasamos la instancia de la aplicación
                'todos_los_bloques': Bloque.objects.all(),
                'todas_las_criticidades': Criticidad.objects.all(),
                'todos_los_estados': Estado.objects.all(),
            }
            # Reutilizamos la misma plantilla de registro
            return render(request, 'gestion/registrar_aplicacion.html', context)
        except Exception as e:
            messages.error(
                request, f'Ocurrió un error al cargar los datos para el formulario: {e}')
            return redirect('gestion:aplicaciones')
