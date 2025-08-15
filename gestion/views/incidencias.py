# gestion/views/incidencias.py

import csv
import io
import re
from datetime import datetime, timedelta

import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from .utils import no_cache, logger
from django.core.exceptions import ObjectDoesNotExist
from unidecode import unidecode
from openpyxl.utils import get_column_letter
from ..models import (Incidencia, Aplicacion, Estado, Severidad, Impacto,
                      GrupoResolutor, Interfaz, Cluster, Bloque, CodigoCierre, Usuario)


@login_required
@no_cache
def incidencias_view(request):
    """
    Renderiza la página de gestión de incidencias y maneja la lógica de filtrado.

    Esta vista tiene un comportamiento especial: si se accede sin ningún
    parámetro de filtro en la URL, aplica automáticamente un filtro para mostrar
    solo las incidencias cuya fecha de última resolución esté dentro del mes actual.
    Si se proporcionan filtros, los aplica a la consulta.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/incidencia.html' con el
                      contexto necesario.

    Context:
        'lista_de_incidencias' (QuerySet): Incidencias resultantes tras el filtrado.
        'total_registros' (int): El número total de incidencias en el sistema.
        'aplicaciones' (QuerySet): Lista de todas las aplicaciones para el filtro.
        'bloques' (QuerySet): Lista de todos los bloques para el filtro.
        'codigos_cierre' (QuerySet): Lista de todos los códigos de cierre para el filtro.
        'fecha_inicio_mes' (str): Primer día del mes actual (formato 'YYYY-MM-DD').
        'fecha_fin_mes' (str): Último día del mes actual (formato 'YYYY-MM-DD').
    """
    # --- 1. Inicio y Registro de Acceso ---
    logger.info(
        f"El usuario '{request.user}' ha accedido a la vista de incidencias.")

    # --- 2. Queryset Base Optimizado ---
    # Usamos select_related para reducir el número de consultas a la base de datos.
    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque', 'codigo_cierre'
    ).all()

    # --- 3. Procesamiento de Filtros ---
    filtros_aplicados = []
    filtro_app_id = request.GET.get('aplicativo')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_incidencia = request.GET.get('incidencia')
    filtro_codigo_id = request.GET.get('codigo_cierre')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')

    # Lógica de filtro por defecto: si no hay filtros en la URL, se usa el mes actual.
    if not request.GET:
        hoy = timezone.now()
        primer_dia_mes = hoy.replace(day=1)
        # Se calcula el último día del mes actual
        if primer_dia_mes.month == 12:
            ultimo_dia_mes = primer_dia_mes.replace(
                year=primer_dia_mes.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            ultimo_dia_mes = primer_dia_mes.replace(
                month=primer_dia_mes.month + 1, day=1) - timedelta(days=1)

        filtro_fecha_desde = primer_dia_mes.strftime('%Y-%m-%d')
        filtro_fecha_hasta = ultimo_dia_mes.strftime('%Y-%m-%d')
        logger.info(
            f"No se proporcionaron filtros. Aplicando filtro por defecto para el mes actual: {filtro_fecha_desde} a {filtro_fecha_hasta}.")

    # Aplicar filtros al queryset solo si el usuario los envía.
    if filtro_app_id and filtro_app_id.isdigit():
        incidencias_qs = incidencias_qs.filter(aplicacion_id=filtro_app_id)
        filtros_aplicados.append(f"aplicativo_id='{filtro_app_id}'")

    if filtro_bloque_id and filtro_bloque_id.isdigit():
        incidencias_qs = incidencias_qs.filter(bloque_id=filtro_bloque_id)
        filtros_aplicados.append(f"bloque_id='{filtro_bloque_id}'")

    if filtro_incidencia:
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)
        filtros_aplicados.append(f"incidencia='{filtro_incidencia}'")

    if filtro_codigo_id and filtro_codigo_id.isdigit():
        incidencias_qs = incidencias_qs.filter(
            codigo_cierre_id=filtro_codigo_id)
        filtros_aplicados.append(f"codigo_cierre_id='{filtro_codigo_id}'")

    # Aplicar filtros de fecha con manejo de errores
    if filtro_fecha_desde:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            fecha_aware = timezone.make_aware(
                fecha_obj, timezone.get_default_timezone())
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_aware)
            filtros_aplicados.append(f"fecha_desde='{filtro_fecha_desde}'")
        except (ValueError, TypeError):
            logger.warning(
                f"Formato de fecha 'desde' inválido: '{filtro_fecha_desde}'. Se ignorará el filtro.")

    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            fecha_aware = timezone.make_aware(
                fecha_obj_fin_dia, timezone.get_default_timezone())
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_aware)
            filtros_aplicados.append(f"fecha_hasta='{filtro_fecha_hasta}'")
        except (ValueError, TypeError):
            logger.warning(
                f"Formato de fecha 'hasta' inválido: '{filtro_fecha_hasta}'. Se ignorará el filtro.")

    if filtros_aplicados and request.GET:  # Solo registrar si los filtros son explícitos del usuario
        logger.info(
            f"Búsqueda de incidencias con filtros: {', '.join(filtros_aplicados)}.")

    logger.info(
        f"La consulta ha devuelto {incidencias_qs.count()} incidencias.")

    # --- 4. Preparación del Contexto para la Plantilla ---
    # Nota: La lógica para calcular las fechas del mes se repite.
    # En una futura refactorización, podría moverse a una función auxiliar.
    hoy = timezone.now()
    primer_dia_mes = hoy.replace(day=1)
    if primer_dia_mes.month == 12:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            year=primer_dia_mes.year + 1, month=1)
    else:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            month=primer_dia_mes.month + 1)
    ultimo_dia_mes = primer_dia_mes_siguiente - timedelta(days=1)

    context = {
        'lista_de_incidencias': incidencias_qs,
        'total_registros': Incidencia.objects.count(),
        'aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
        'bloques': Bloque.objects.all().order_by('desc_bloque'),
        'codigos_cierre': CodigoCierre.objects.all().order_by('cod_cierre'),
        'fecha_inicio_mes': primer_dia_mes.strftime('%Y-%m-%d'),
        'fecha_fin_mes': ultimo_dia_mes.strftime('%Y-%m-%d'),
    }

    # --- 5. Renderizado Final ---
    return render(request, 'gestion/incidencia.html', context)


@login_required
@no_cache
def registrar_incidencia_view(request):
    """
    Gestiona la visualización del formulario y el registro de una nueva incidencia.

    Esta vista maneja dos flujos basados en el método HTTP:
    - GET: Muestra un formulario vacío para que el usuario ingrese los datos de
      una nueva incidencia. Carga todas las listas de objetos relacionados
      (aplicaciones, estados, etc.) para los campos de selección.
    - POST: Procesa los datos enviados desde el formulario. Crea una nueva
      instancia del modelo `Incidencia`, la guarda en la base de datos y
      redirige al usuario a la lista de incidencias.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse:
            - Si el método es GET, renderiza la plantilla 'gestion/registrar_incidencia.html'.
            - Si el método es POST, redirige a 'gestion:incidencias' tras un
              registro exitoso, o vuelve a renderizar el formulario con los
              datos ingresados en caso de error.

    Context (solo en GET o en error de POST):
        'aplicaciones' (QuerySet): Lista de todas las aplicaciones.
        'estados' (QuerySet): Lista de estados de tipo 'Incidencia'.
        'severidades' (QuerySet): Lista de todas las severidades.
        ...y así para todos los modelos relacionados.
        'form_data' (dict, opcional): Los datos del POST si ocurre un error,
                                     para no perder la información ingresada.
    """

    def get_context_data():
        """Función auxiliar para obtener los datos de los selectores del formulario."""
        return {
            'aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
            'estados': Estado.objects.filter(uso_estado='Incidencia').order_by('desc_estado'),
            'severidades': Severidad.objects.all(),
            'impactos': Impacto.objects.all(),
            'grupos_resolutores': GrupoResolutor.objects.all(),
            'interfaces': Interfaz.objects.all(),
            'clusters': Cluster.objects.all(),
            'bloques': Bloque.objects.all(),
            'usuarios': Usuario.objects.all().order_by('nombre'),
        }

    # --- Escenario 1: El usuario envía datos para crear un registro (POST) ---
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de registro de incidencia.")
        try:
            # --- 1. Obtención de Objetos Relacionados ---
            # Se obtienen las instancias de los modelos foráneos a partir de los IDs enviados.
            # Un ID inválido aquí lanzará una excepción que será capturada.
            aplicacion_obj = Aplicacion.objects.get(
                pk=request.POST.get('aplicacion'))
            estado_obj = Estado.objects.get(pk=request.POST.get('estado'))
            impacto_obj = Impacto.objects.get(pk=request.POST.get('impacto'))
            bloque_obj = Bloque.objects.get(pk=request.POST.get('bloque'))

            # Campos opcionales: se obtienen solo si el usuario seleccionó un valor.
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
            usuario_asignado_obj = Usuario.objects.get(pk=request.POST.get(
                'usuario_asignado')) if request.POST.get('usuario_asignado') else None

            # --- 2. Procesamiento de Datos del Formulario ---
            fecha_apertura_str = request.POST.get('fecha_apertura')
            fecha_apertura_obj = datetime.fromisoformat(
                fecha_apertura_str) if fecha_apertura_str else None
            fecha_resolucion_str = request.POST.get('fecha_ultima_resolucion')
            fecha_resolucion_obj = datetime.fromisoformat(
                fecha_resolucion_str) if fecha_resolucion_str else None

            # --- 3. Creación y Guardado de la Instancia ---
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
                usuario_asignado=usuario_asignado_obj,
                demandas=request.POST.get('demandas', ''),
                workaround=request.POST.get('workaround', 'No'),
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
                f"Usuario '{request.user}' registró con éxito la incidencia '{nueva_incidencia.incidencia}'.")
            messages.success(
                request, f'¡La incidencia "{nueva_incidencia.incidencia}" ha sido registrada con éxito!')
            return redirect('gestion:incidencias')

        except Exception as e:
            # Si ocurre cualquier error, se registra y se devuelve al usuario al formulario.
            logger.error(
                f"Error al registrar incidencia por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error inesperado al guardar la incidencia: {e}. Por favor, revisa los datos.')
            context = get_context_data()
            # Se devuelven los datos para no perderlos.
            context['form_data'] = request.POST
            return render(request, 'gestion/registrar_incidencia.html', context)

    # --- Escenario 2: El usuario solicita ver el formulario (GET) ---
    else:
        logger.info(
            f"El usuario '{request.user}' está viendo el formulario para registrar una nueva incidencia.")
        try:
            context = get_context_data()
            return render(request, 'gestion/registrar_incidencia.html', context)
        except Exception as e:
            logger.error(
                f"Error al cargar datos para el formulario de registro: {e}", exc_info=True)
            messages.error(
                request, 'Ocurrió un error al cargar la página de registro.')
            return redirect('gestion:dashboard')


@login_required
@no_cache
def editar_incidencia_view(request, pk):
    """
    Gestiona la visualización del formulario y la actualización de una incidencia existente.

    Esta vista maneja dos flujos basados en el método HTTP:
    - GET: Busca la incidencia por su 'pk'. Si la encuentra, muestra el formulario
      de registro pre-poblado con los datos de esa incidencia.
    - POST: Procesa los datos enviados desde el formulario. Actualiza el objeto
      de la incidencia con los nuevos valores, lo guarda en la base de datos y
      redirige al usuario a la lista de incidencias.

    Si la incidencia con el 'pk' dado no existe, devuelve un error 404.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria de la incidencia a editar.

    Returns:
        HttpResponse: Renderiza la plantilla, redirige, o devuelve un error 404.

    Context (solo en GET o en error de POST):
        'incidencia' (Incidencia): La instancia de la incidencia que se está editando.
        'form_data' (dict, opcional): Los datos del POST si ocurre un error,
                                     para no perder la información ingresada.
        ...y todas las listas para los selectores (aplicaciones, estados, etc.).
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
            'estados': Estado.objects.filter(uso_estado='Incidencia').order_by('desc_estado'),
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

            # Fechas
            fecha_apertura_str = request.POST.get('fecha_apertura')
            incidencia.fecha_apertura = datetime.fromisoformat(
                fecha_apertura_str) if fecha_apertura_str else None
            fecha_resolucion_str = request.POST.get('fecha_ultima_resolucion')
            incidencia.fecha_ultima_resolucion = datetime.fromisoformat(
                fecha_resolucion_str) if fecha_resolucion_str else None

            # Campos de texto
            incidencia.causa = request.POST.get('causa', '')
            incidencia.bitacora = request.POST.get('bitacora', '')
            incidencia.tec_analisis = request.POST.get('tec_analisis', '')
            incidencia.correccion = request.POST.get('correccion', '')
            incidencia.solucion_final = request.POST.get('solucion_final', '')
            incidencia.observaciones = request.POST.get('observaciones', '')
            incidencia.demandas = request.POST.get('demandas', '')
            incidencia.workaround = request.POST.get('workaround', 'No')

            # Relaciones (Foreign Keys)
            incidencia.aplicacion = Aplicacion.objects.get(
                pk=request.POST.get('aplicacion'))
            incidencia.estado = Estado.objects.get(
                pk=request.POST.get('estado'))
            incidencia.impacto = Impacto.objects.get(
                pk=request.POST.get('impacto'))
            incidencia.bloque = Bloque.objects.get(
                pk=request.POST.get('bloque'))

            # Relaciones opcionales
            incidencia.severidad = Severidad.objects.get(pk=request.POST.get(
                'severidad')) if request.POST.get('severidad') else None
            incidencia.grupo_resolutor = GrupoResolutor.objects.get(pk=request.POST.get(
                'grupo_resolutor')) if request.POST.get('grupo_resolutor') else None
            incidencia.interfaz = Interfaz.objects.get(pk=request.POST.get(
                'interfaz')) if request.POST.get('interfaz') else None
            incidencia.cluster = Cluster.objects.get(pk=request.POST.get(
                'cluster')) if request.POST.get('cluster') else None
            incidencia.codigo_cierre = CodigoCierre.objects.get(pk=request.POST.get(
                'codigo_cierre')) if request.POST.get('codigo_cierre') else None
            incidencia.usuario_asignado = Usuario.objects.get(pk=request.POST.get(
                'usuario_asignado')) if request.POST.get('usuario_asignado') else None

            # Guardamos los cambios en la base de datos
            incidencia.save()

            messages.success(
                request, f'¡La incidencia "{incidencia.incidencia}" ha sido actualizada con éxito!')
            return redirect('gestion:incidencias')

        except (ObjectDoesNotExist, ValueError) as e:
            logger.error(
                f"Error al editar incidencia '{incidencia.id}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al actualizar la incidencia: {e}. Por favor, revisa los campos.')

            context = get_context_data()
            # Reenviamos la incidencia original y los datos del POST para no perder los cambios
            context['incidencia'] = incidencia
            context['form_data'] = request.POST
            return render(request, 'gestion/registrar_incidencia.html', context)

    else:  # Si es método GET, mostramos el formulario con los datos actuales
        context = get_context_data()
        # Añadimos la incidencia al contexto
        context['incidencia'] = incidencia
        return render(request, 'gestion/registrar_incidencia.html', context)


@login_required
@no_cache
def eliminar_incidencia_view(request, pk):
    """
    Gestiona la eliminación de una incidencia específica.

    Esta vista está protegida para aceptar únicamente peticiones POST como
    medida de seguridad, previniendo eliminaciones accidentales a través de
    enlaces (peticiones GET). Busca la incidencia por su clave primaria (pk)
    y, si la encuentra, la elimina.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria (ID) de la incidencia a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la vista 'gestion:incidencias'
                      después de intentar la operación.
    """
    # Se valida que la petición sea POST para proceder con la eliminación.
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de eliminación para la incidencia con ID: {pk}.")
        try:
            # get_object_or_404 es la forma recomendada de obtener un objeto.
            # Si no lo encuentra, detendrá la ejecución y mostrará una página de "No Encontrado".
            incidencia = get_object_or_404(Incidencia, pk=pk)
            nombre_incidencia = incidencia.incidencia

            # Se elimina el objeto de la base de datos.
            incidencia.delete()

            # Se registra la eliminación como una ADVERTENCIA (WARNING) para que sea
            # fácil de localizar en los logs, ya que es una acción destructiva importante.
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO la incidencia '{nombre_incidencia}' (ID: {pk})."
            )
            messages.success(
                request, f'La incidencia "{nombre_incidencia}" ha sido eliminada correctamente.')

        except Exception as e:
            # Captura cualquier error inesperado durante la eliminación.
            # Esto puede incluir la excepción Http404 de get_object_or_404 si el ID no existe,
            # o errores de la base de datos (ej. por restricciones de clave foránea).
            logger.error(
                f"Error al intentar eliminar la incidencia ID {pk} por el usuario '{request.user}'. Error: {e}",
                # Registra el traceback completo para facilitar la depuración.
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al eliminar la incidencia: {e}')

    # Si la petición no es POST, o después de la operación, se redirige.
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


def normalize_text(text):
    """Convierte texto a minúsculas y quita acentos."""
    if text is None:
        return ""
    return unidecode(str(text)).lower().strip()


@login_required
@no_cache
def carga_masiva_incidencia_view(request):
    """
    Gestiona la carga masiva de incidencias.
    (Versión que crea si no existe, o informa si ya existe sin actualizar).
    """
    # ... (bloque try/except para las cachés sin cambios) ...
    try:
        # --- Creación de Cachés de Búsqueda ---
        aplicacion_cache = {normalize_text(
            a.cod_aplicacion): a for a in Aplicacion.objects.all()}
        estado_cache = {normalize_text(
            e.desc_estado): e for e in Estado.objects.all()}
        severidad_cache = {normalize_text(
            s.desc_severidad): s for s in Severidad.objects.all()}
        cluster_cache = {normalize_text(
            c.desc_cluster): c for c in Cluster.objects.all()}
        bloque_cache = {normalize_text(
            b.desc_bloque): b for b in Bloque.objects.all()}
        usuario_cache = {normalize_text(
            u.usuario): u for u in Usuario.objects.all()}
        grupo_resolutor_cache = {normalize_text(
            g.desc_grupo_resol): g for g in GrupoResolutor.objects.all()}

        default_impacto = Impacto.objects.get(desc_impacto__iexact='interno')
        default_interfaz = Interfaz.objects.get(desc_interfaz__iexact='WEB')

        # --- NUEVO: Precargar estados clave para la lógica de actualización ---
        estado_cerrado = Estado.objects.get(desc_estado__iexact='Cerrado')
        estado_cancelado = Estado.objects.get(
            desc_estado__iexact='Cancelado')
        estado_resuelto = Estado.objects.get(desc_estado__iexact='Resuelto')
        estados_finales = [estado_cerrado, estado_cancelado]
        # --- FIN DE LA MODIFICACIÓN ---

    except ObjectDoesNotExist as e:
        messages.error(
            request, f"Error de Configuración: No se encontró un valor por defecto. Error: {e}")
        return redirect('gestion:carga_masiva_incidencia')

    if request.method == 'POST':
        file = request.FILES.get('csv_file')
        if not file or not (file.name.endswith('.csv') or file.name.endswith('.xlsx')):
            messages.error(
                request, 'Por favor, selecciona un archivo con formato .csv o .xlsx.')
            return redirect('gestion:carga_masiva_incidencia')

        # <<<--- PASO 1: AJUSTAR CONTADORES ---<<<
        failed_rows = []
        new_indra_d_count = 0
        new_normal_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            # ... (código de lectura de archivo sin cambios) ...
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, keep_default_na=False, dtype=str)
            else:
                df = pd.read_excel(file, keep_default_na=False, dtype=str)
            df.fillna('', inplace=True)

            with transaction.atomic():
                for index, row in df.iterrows():
                    line_number = index + 2
                    try:
                        incidencia_id = row['incidencia'].strip()
                        if not incidencia_id or not incidencia_id.upper().startswith('INC'):
                            continue

                        # ... (Toda la lógica de asignación de objetos sin cambios) ...
                        aplicacion_obj = None
                        codigo_cierre_obj = None
                        app_val = row['aplicacion_id'].strip()
                        cc_val = row['codigo_cierre_id'].strip()

                        if app_val and cc_val:
                            temp_app = aplicacion_cache.get(
                                normalize_text(app_val))
                            if temp_app:
                                try:
                                    temp_cc = CodigoCierre.objects.get(
                                        cod_cierre__iexact=cc_val, aplicacion=temp_app)
                                    aplicacion_obj = temp_app
                                    codigo_cierre_obj = temp_cc
                                except CodigoCierre.DoesNotExist:
                                    aplicacion_obj = None
                                    codigo_cierre_obj = None
                            else:
                                aplicacion_obj = None
                                codigo_cierre_obj = None
                        elif app_val and not cc_val:
                            aplicacion_obj = aplicacion_cache.get(
                                normalize_text(app_val))
                        elif not app_val and cc_val:
                            try:
                                temp_cc = CodigoCierre.objects.get(
                                    cod_cierre__iexact=cc_val)
                                codigo_cierre_obj = temp_cc
                                aplicacion_obj = temp_cc.aplicacion
                            except (CodigoCierre.DoesNotExist, CodigoCierre.MultipleObjectsReturned):
                                aplicacion_obj = None
                                codigo_cierre_obj = None

                        estado_obj = estado_cache.get(
                            normalize_text(row['estado_id']))
                        severidad_obj = severidad_cache.get(
                            normalize_text(row['severidad_id']))
                        cluster_obj = cluster_cache.get(
                            normalize_text(row['cluster_id']))

                        bloque_val = normalize_text(row['bloque_id'])
                        is_indra_d_row = (bloque_val == 'indra_d')
                        bloque_obj = None
                        grupo_resolutor_obj = None

                        if is_indra_d_row:
                            # Asignación especial para 'indra_d': se asigna bloque 'Sin bloque' y grupo 'INDRA_D'
                            bloque_obj = bloque_cache.get(
                                normalize_text('Sin bloque'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('INDRA_D'))
                        elif bloque_val == 'indra_b3':
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 3'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_3B'))
                        elif bloque_val in ('indra', 'indra_a'):
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 4'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_G3'))
                        elif bloque_val in ('indra', 'indra_a'):
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 4'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_G5'))
                        elif bloque_val in ('indra', 'indra_a'):
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 4'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_G11'))
                        elif bloque_val in ('indra', 'indra_a'):
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 4'))
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('INDRA N2'))

                        impacto_obj = default_impacto
                        interfaz_obj = default_interfaz
                        usuario_asignado_obj = usuario_cache.get(
                            normalize_text(row['usuario_asignado_id']))
                        workaround_val = 'Sí' if 'con wa' in row['workaround'].strip(
                        ).lower() else 'No'

                        # --- LÓGICA DE CREACIÓN O ACTUALIZACIÓN ---
                        try:
                            existing_incidence = Incidencia.objects.get(
                                incidencia=incidencia_id)

                            # --- LÓGICA PARA INCIDENCIAS EXISTENTES ---
                            if existing_incidence.estado in estados_finales:
                                skipped_count += 1
                                logger.info(
                                    f"Incidencia {incidencia_id} omitida (estado final).")
                                continue

                            if existing_incidence.estado == estado_resuelto and estado_obj in estados_finales:
                                old_state_desc = existing_incidence.estado.desc_estado
                                existing_incidence.estado = estado_obj
                                if fecha_resolucion_str := row['fecha_ultima_resolucion'].strip():
                                    existing_incidence.fecha_ultima_resolucion = timezone.make_aware(
                                        datetime.strptime(fecha_resolucion_str, '%d-%m-%Y %H:%M:%S'))
                                existing_incidence.save(
                                    update_fields=['estado', 'fecha_ultima_resolucion'])
                                updated_count += 1
                                logger.info(
                                    f"Incidencia {incidencia_id} ACTUALIZADA de '{old_state_desc}' a '{estado_obj.desc_estado}'.")
                            else:
                                skipped_count += 1
                                logger.info(
                                    f"Incidencia {incidencia_id} omitida (no requiere actualización de estado).")

                        except Incidencia.DoesNotExist:
                            # --- LÓGICA PARA NUEVAS INCIDENCIAS ---
                            Incidencia.objects.create(
                                incidencia=incidencia_id,
                                descripcion_incidencia=row['descripcion_incidencia'].strip(
                                ),
                                fecha_apertura=timezone.make_aware(datetime.strptime(row['fecha_apertura'].strip(
                                ), '%d-%m-%Y %H:%M:%S')) if row['fecha_apertura'].strip() else None,
                                fecha_ultima_resolucion=timezone.make_aware(datetime.strptime(row['fecha_ultima_resolucion'].strip(
                                ), '%d-%m-%Y %H:%M:%S')) if row['fecha_ultima_resolucion'].strip() else None,
                                causa=row['causa'].strip(),
                                bitacora=row['bitacora'].strip(),
                                tec_analisis=row['tec_analisis'].strip(),
                                correccion=row['correccion'].strip(),
                                solucion_final=row['solucion_final'].strip(),
                                observaciones=row['observaciones'].strip(),
                                demandas=row['demanadas'].strip(),
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
                                usuario_asignado=usuario_asignado_obj,
                            )
                            if is_indra_d_row:
                                new_indra_d_count += 1
                            else:
                                new_normal_count += 1
                            logger.info(
                                f"Incidencia {incidencia_id} CREADA con éxito.")

                    except Exception as e:
                        logger.error(
                            f"Error procesando fila {line_number} (Incidencia: {incidencia_id}): {e}", exc_info=True)
                        failed_rows.append({'line': line_number, 'row_data': ', '.join(
                            map(str, row.values)), 'error': str(e)})

            # <<<--- PASO 4: AJUSTAR RESUMEN FINAL ---<<<
            total_creadas = new_indra_d_count + new_normal_count
            log_summary = f"""
            \n--------------------------------------------------
            \nRESUMEN DE CARGA MASIVA
            \nUsuario: {request.user}
            \nArchivo: {file.name}
            \n--------------------------------------------------
            \nTotal de filas leídas del archivo: {len(df)}
            \nIncidencias 'INDRA_D' creadas: {new_indra_d_count}
            \nIncidencias 'Normales' creadas: {new_normal_count}
            \nTotal de incidencias nuevas creadas: {total_creadas}
            \nIncidencias actualizadas (estado): {updated_count}
            \nIncidencias omitidas (ya existían): {skipped_count}
            \nIncidencias con errores: {len(failed_rows)}
            \n--------------------------------------------------
            """
            if failed_rows:
                log_summary += "\nDETALLE DE ERRORES:\n"
                for item in failed_rows:
                    incidencia_id_error = item.get(
                        'row_data', 'N/A').split(',')[0]
                    log_summary += f"  - Fila {item['line']} (Incidencia: {incidencia_id_error}): {item['error']}\n"
                log_summary += "--------------------------------------------------\n"

            logger.info(log_summary)

            if total_creadas > 0:
                messages.success(
                    request, f'¡Carga completada! Total creadas: {total_creadas} (INDRA_D: {new_indra_d_count}, Normales: {new_normal_count}).')
            if updated_count > 0:
                messages.info(
                    request, f'Se actualizaron {updated_count} incidencias que estaban resueltas.')
            if skipped_count > 0:
                messages.info(
                    request, f'Se omitieron {skipped_count} incidencias que ya existían y no requerían actualización.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Por favor, revisa los detalles.')

            return render(request, 'gestion/carga_masiva_incidencia.html', {'failed_rows': failed_rows})

        except Exception as e:
            logger.error(
                f"Error crítico al leer o procesar el archivo '{file.name}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al leer o procesar el archivo: {e}')
            return redirect('gestion:carga_masiva_incidencia')

    return render(request, 'gestion/carga_masiva_incidencia.html')


# VISTA NUEVA PARA EXPORTAR EL REPORTE EN FORMATO XLSX
@login_required
@no_cache
def exportar_incidencias_reporte_view(request):
    """
    Genera y exporta un reporte de incidencias en formato .xlsx,
    respetando los filtros aplicados en la vista principal.
    """
    logger.info(
        f"Usuario '{request.user}' ha solicitado un reporte de incidencias en Excel.")

    # 1. Queryset base optimizado (igual que en incidencias_view)
    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque',
        'codigo_cierre', 'grupo_resolutor'
    ).all()

    # 2. Replicar la lógica de filtrado de incidencias_view
    # Esto es crucial para que el reporte coincida con la tabla visible
    filtro_app_id = request.GET.get('aplicativo')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_incidencia = request.GET.get('incidencia')
    filtro_codigo_id = request.GET.get('codigo_cierre')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')

    if filtro_app_id and filtro_app_id.isdigit():
        incidencias_qs = incidencias_qs.filter(aplicacion_id=filtro_app_id)
    if filtro_bloque_id and filtro_bloque_id.isdigit():
        incidencias_qs = incidencias_qs.filter(bloque_id=filtro_bloque_id)
    if filtro_incidencia:
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)
    if filtro_codigo_id and filtro_codigo_id.isdigit():
        incidencias_qs = incidencias_qs.filter(
            codigo_cierre_id=filtro_codigo_id)
    if filtro_fecha_desde:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=timezone.make_aware(fecha_obj))
        except (ValueError, TypeError):
            pass
    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=timezone.make_aware(fecha_obj_fin_dia))
        except (ValueError, TypeError):
            pass

    # 3. Preparar los datos para el DataFrame de Pandas
    meses_es = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    data_para_excel = []
    for inc in incidencias_qs:
        mes_resolucion = ""
        fecha_resolucion_str = ""
        if inc.fecha_ultima_resolucion:
            # Hacemos la fecha consciente a la zona horaria local para extraer el mes correcto
            fecha_local = timezone.localtime(inc.fecha_ultima_resolucion)
            mes_resolucion = meses_es.get(fecha_local.month, '')
            fecha_resolucion_str = fecha_local.strftime('%d-%m-%Y %H:%M')

        data_para_excel.append({
            'ID de la Incidencia': inc.incidencia,
            'Criticidad aplicativo': inc.aplicacion.criticidad.desc_criticidad if inc.aplicacion and inc.aplicacion.criticidad else 'N/A',
            'severidad incidencia': inc.severidad.desc_severidad if inc.severidad else 'N/A',
            'Grupo resolutor': inc.grupo_resolutor.desc_grupo_resol if inc.grupo_resolutor else 'N/A',
            'Aplicativo': inc.aplicacion.nombre_aplicacion if inc.aplicacion else 'N/A',
            'Fecha de Resolucion': fecha_resolucion_str,
            'mes': mes_resolucion,
            'cod_cierre': inc.codigo_cierre.cod_cierre if inc.codigo_cierre else 'N/A',
            'Descripción Cierre': inc.codigo_cierre.desc_cod_cierre if inc.codigo_cierre else 'N/A',
            'Bloque': inc.bloque.desc_bloque if inc.bloque else 'N/A'
        })

    # 4. Crear el archivo Excel en memoria usando Pandas
    df = pd.DataFrame(data_para_excel)
    output = io.BytesIO()

    # Escribir el DataFrame al buffer de BytesIO como un archivo Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Incidencias')
        worksheet = writer.sheets['Reporte Incidencias']
        # Opcional: Auto-ajustar el ancho de las columnas
        for column in df:
            column_length = max(df[column].astype(
                str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[get_column_letter(
                col_idx + 1)].width = column_length + 2

    output.seek(0)  # Mover el cursor al inicio del stream

    # 5. Crear la respuesta HTTP para descargar el archivo
    filename = f"Reporte_Incidencias_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Se establece una cookie para que el frontend pueda ocultar el spinner
    response.set_cookie('descargaFinalizada', 'true', max_age=20, path='/')

    return response


# Coloca esta función auxiliar justo antes de tu vista carga_masiva_inicial_view
def _parse_complex_txt_file(file_content):
    """
    Función auxiliar para parsear el complejo formato de archivo .txt multi-línea.
    """
    logger.info("Iniciando el parseo del archivo TXT complejo.")

    fixed_header = [
        'id_incidencia', 'id_aplicacion', 'incidencia', 'descripcion_incidencia', 'fecha_apertura',
        'fecha_ultima_resolucion', 'id_estado', 'id_criticidad', 'id_grupo_resolutor', 'sistema_modulo',
        'id_interfaz', 'componente', 'componente_afectado', 'componente_relacionado', 'evidencia',
        'causa', 'bitacora', 'tec_analisis', 'correccion', 'solucion_final', 'casuistica',
        'id_impacto', 'id_it', 'id_cluster', 'codigo_app_remedy', 'observaciones', 'gestion_n3',
        'nro_peticiones', 'id_bloque', 'usuario_asignado', 'workaround', 'demandas', 'excepciones',
        'grupo_asignado', 'codigo_aplicacion', 'cod_cierre'
    ]
    logger.info(f"Usando cabecera fija con {len(fixed_header)} columnas.")

    # Busca el separador de cabecera para aislar el cuerpo de los datos
    separator_match = re.search(r'\s*\|-{10,}.*?\n', file_content)
    if not separator_match:
        raise ValueError(
            "No se encontró la línea separadora de la cabecera ('|---|') en el archivo.")

    # El cuerpo de datos es todo lo que viene después del separador
    data_body = file_content[separator_match.end():]

    # --- CAMBIO DE ESTRATEGIA: Dividir por el inicio de una nueva línea de registro ---
    # Un nuevo registro empieza con un pipe, un número, espacios y otro pipe.
    record_blocks = re.split(r'\n(?=\s*\|\s*\d+\s*\|)', data_body)

    parsed_data = []
    for line_num, block in enumerate(record_blocks, start=1):
        if not block.strip():
            continue

        lines = block.strip().splitlines()
        structured_line = lines[0] if lines else ""
        unstructured_text = '\n'.join(lines[1:])

        if not structured_line:
            continue

        values = [v.strip() for v in structured_line.split('|')[1:]]
        row_data = dict(zip(fixed_header, values))

        # Asigna el texto largo a los campos correspondientes.
        if not row_data.get('bitacora'):
            row_data['bitacora'] = unstructured_text

        row_data['original_line_num'] = line_num
        parsed_data.append(row_data)

    logger.info(
        f"Parseo finalizado. Se extrajeron {len(parsed_data)} registros del archivo.")
    return parsed_data


@login_required
@transaction.atomic
def carga_masiva_inicial_view(request):
    """
    Gestiona la carga masiva de incidencias desde un archivo .txt con formato de reporte.
    """
    if request.method != 'POST':
        return render(request, 'gestion/carga_masiva_inicial.html')

    logger.info(
        f"Usuario '{request.user}' ha iniciado una carga masiva inicial de incidencias.")
    file = request.FILES.get('incidencias_file')

    if not file or not file.name.endswith('.txt'):
        messages.error(request, 'El archivo debe tener extensión .txt')
        return redirect('gestion:carga_masiva_inicial')

    try:
        logger.info("Precargando catálogos en memoria para validación...")
        aplicacion_cache = {str(a.id): a for a in Aplicacion.objects.all()}
        estado_cache = {str(e.id): e for e in Estado.objects.all()}
        impacto_cache = {str(i.id): i for i in Impacto.objects.all()}
        bloque_cache = {str(b.id): b for b in Bloque.objects.all()}
        grupo_resolutor_cache = {
            str(g.id): g for g in GrupoResolutor.objects.all()}
        interfaz_cache = {str(i.id): i for i in Interfaz.objects.all()}
        cluster_cache = {str(c.id): c for c in Cluster.objects.all()}
        usuario_cache = {unidecode(u.nombre).lower(
        ).strip(): u for u in Usuario.objects.all()}
        codigo_cierre_cache = {(cc.cod_cierre, cc.aplicacion_id)
                                : cc for cc in CodigoCierre.objects.select_related('aplicacion')}
        logger.info("Cachés creadas con éxito.")

        file_content = file.read().decode('utf-8', errors='replace')
        all_rows_data = _parse_complex_txt_file(file_content)

        errors, created_count, skipped_count = [], 0, 0

        for row_data in all_rows_data:
            line_num = row_data['original_line_num']
            incidencia_id = row_data.get('incidencia')
            try:
                # --- ✅ VALIDACIÓN REFORZADA AL INICIO ---
                if not incidencia_id:
                    raise ValueError(
                        'La columna "incidencia" no puede estar vacía.')

                if Incidencia.objects.filter(incidencia=incidencia_id).exists():
                    skipped_count += 1
                    logger.info(
                        f"--- Procesando Registro #{line_num} (Incidencia: {incidencia_id}) ---\n  -> OMITIDO: La incidencia ya existe.")
                    continue

                logger.info(
                    f"--- Procesando Registro #{line_num} (Incidencia: {incidencia_id}) ---")

                # Búsqueda y validación de objetos OBLIGATORIOS
                id_aplicacion = row_data.get('id_aplicacion')
                aplicacion_obj = aplicacion_cache.get(id_aplicacion)
                if not aplicacion_obj:
                    raise ValueError(
                        f"ID de Aplicación no encontrado en la BD: '{id_aplicacion}'")

                id_estado = row_data.get('id_estado')
                estado_obj = estado_cache.get(id_estado)
                if not estado_obj:
                    raise ValueError(
                        f"ID de Estado no encontrado en la BD: '{id_estado}'")

                id_impacto = row_data.get('id_impacto')
                impacto_obj = impacto_cache.get(id_impacto)
                if not impacto_obj:
                    raise ValueError(
                        f"ID de Impacto no encontrado en la BD: '{id_impacto}'")

                # Búsqueda de objetos opcionales
                grupo_resolutor_obj = grupo_resolutor_cache.get(
                    row_data.get('id_grupo_resolutor'))
                interfaz_obj = interfaz_cache.get(row_data.get('id_interfaz'))
                cluster_obj = cluster_cache.get(row_data.get('id_cluster'))
                bloque_obj = bloque_cache.get(row_data.get('id_bloque'))
                severidad_obj = severidad_cache.get(
                    row_data.get('id_criticidad'))

                usuario_asignado_obj = None
                if nombre_usuario := row_data.get('usuario_asignado', '').strip():
                    usuario_asignado_obj = usuario_cache.get(
                        unidecode(nombre_usuario).lower().strip())

                codigo_cierre_obj = None
                if cod_cierre_val := row_data.get('cod_cierre', '').strip():
                    codigo_cierre_obj = codigo_cierre_cache.get(
                        (cod_cierre_val, aplicacion_obj.id))

                # Manejo de Fechas
                fecha_apertura_obj = None
                if fecha_str := row_data.get('fecha_apertura'):
                    fecha_apertura_obj = timezone.make_aware(
                        datetime.strptime(fecha_str.split()[0], '%Y-%m-%d'))

                fecha_resolucion_obj = None
                if fecha_str := row_data.get('fecha_ultima_resolucion'):
                    fecha_resolucion_obj = timezone.make_aware(
                        datetime.strptime(fecha_str.split()[0], '%Y-%m-%d'))

                # Creación del objeto Incidencia
                Incidencia.objects.create(
                    incidencia=incidencia_id, aplicacion=aplicacion_obj, estado=estado_obj, impacto=impacto_obj,
                    descripcion_incidencia=row_data.get(
                        'descripcion_incidencia', ''),
                    fecha_apertura=fecha_apertura_obj, fecha_ultima_resolucion=fecha_resolucion_obj,
                    grupo_resolutor=grupo_resolutor_obj, interfaz=interfaz_obj, cluster=cluster_obj,
                    bloque=bloque_obj, severidad=severidad_obj, usuario_asignado=usuario_asignado_obj,
                    codigo_cierre=codigo_cierre_obj,
                    causa=row_data.get('causa', ''), bitacora=row_data.get('bitacora', ''),
                    tec_analisis=row_data.get('tec_analisis', ''), correccion=row_data.get('correccion', ''),
                    solucion_final=row_data.get('solucion_final', ''), observaciones=row_data.get('observaciones', ''),
                    demandas=row_data.get('demandas', ''),
                    workaround='No' if not row_data.get(
                        'workaround') else row_data.get('workaround')
                )
                created_count += 1
                logger.info(
                    f"  -> ¡ÉXITO! Incidencia '{incidencia_id}' creada.")

            except Exception as e:
                errors.append(
                    {'line': line_num, 'incidencia': incidencia_id, 'message': str(e)})
                logger.error(
                    f"  -> ERROR en Registro #{line_num} (Incidencia: {incidencia_id}): {e}")

        # --- RESUMEN FINAL DE LA CARGA ---
        if errors:
            transaction.set_rollback(True)
            logger.warning(
                f"La carga masiva falló con {len(errors)} errores. Revirtiendo transacción.")
            messages.error(
                request, f'La carga fue cancelada. Se encontraron {len(errors)} errores. Ninguna incidencia fue guardada.')
            return render(request, 'gestion/carga_masiva_inicial.html', {'errors': errors})

        final_message = f'Carga masiva completada con éxito. Se crearon {created_count} incidencias nuevas.'
        if skipped_count > 0:
            final_message += f' Se omitieron {skipped_count} incidencias que ya existían.'

        logger.info(final_message)
        messages.success(request, final_message)
        return redirect('gestion:incidencias')

    except Exception as e:
        logger.critical(
            f"Error crítico durante la carga masiva: {e}", exc_info=True)
        messages.error(
            request, f'Ocurrió un error inesperado al procesar el archivo: {e}')
        return redirect('gestion:carga_masiva_inicial')
