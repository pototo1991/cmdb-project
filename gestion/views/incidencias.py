# gestion/views/incidencias.py

import csv
import io
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Q
from django.utils import timezone
from django.db import transaction
from .utils import no_cache, logger
from ..models import Aplicacion, Estado, Severidad, Impacto, GrupoResolutor, Interfaz, Cluster, Bloque, Incidencia, CodigoCierre, Usuario
from django.core.exceptions import ObjectDoesNotExist
from unidecode import unidecode
from openpyxl.utils import get_column_letter


@login_required
@no_cache
def incidencias_view(request):
    """
    Maneja la lógica para la página de gestión de incidencias.
    Muestra todos los registros por defecto y permite filtrar.
    """
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de incidencias.")

    # 1. Queryset base optimizado.
    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque', 'codigo_cierre'
    ).all()

    # 2. Obtener valores de los filtros desde la URL (request.GET)
    filtro_app_id = request.GET.get('aplicativo')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_incidencia = request.GET.get('incidencia')
    filtro_codigo_id = request.GET.get('codigo_cierre')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')

    # 3. Aplicar filtros al queryset solo si el usuario los envía
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
            fecha_aware = timezone.make_aware(
                fecha_obj, timezone.get_default_timezone())
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_aware)
        except (ValueError, TypeError):
            pass

    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            fecha_aware = timezone.make_aware(
                fecha_obj_fin_dia, timezone.get_default_timezone())
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_aware)
        except (ValueError, TypeError):
            pass

    # --- INICIO DE LA MODIFICACIÓN ---
    # 4. Calcular siempre las fechas del mes actual para el botón "Ver Mes Actual"
    hoy = timezone.now()
    primer_dia_mes = hoy.replace(day=1)

    if primer_dia_mes.month == 12:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            year=primer_dia_mes.year + 1, month=1)
    else:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            month=primer_dia_mes.month + 1)

    ultimo_dia_mes = primer_dia_mes_siguiente.replace(
        day=1) - timedelta(days=1)

    # 5. Obtener todos los objetos para llenar los <select> de los filtros
    aplicaciones = Aplicacion.objects.all().order_by('nombre_aplicacion')
    bloques = Bloque.objects.all().order_by('desc_bloque')
    codigos_cierre = CodigoCierre.objects.all().order_by('cod_cierre')

    # 6. Preparar el contexto para la plantilla
    context = {
        'lista_de_incidencias': incidencias_qs,
        'total_registros': Incidencia.objects.count(),
        'aplicaciones': aplicaciones,
        'bloques': bloques,
        'codigos_cierre': codigos_cierre,
        # Añadimos las fechas formateadas para usarlas en el link del botón
        'fecha_inicio_mes': primer_dia_mes.strftime('%Y-%m-%d'),
        'fecha_fin_mes': ultimo_dia_mes.strftime('%Y-%m-%d'),
    }
    # --- FIN DE LA MODIFICACIÓN ---

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
        new_incidents_count = 0
        existing_skipped_count = 0  # <-- Nuevo contador
        skipped_indra_d_count = 0

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
                        if bloque_val == 'indra_d':
                            skipped_indra_d_count += 1
                            logger.info(
                                f"Omitiendo incidencia {incidencia_id} (fila {line_number}) por valor 'indra_d'.")
                            continue

                        bloque_obj = None
                        if bloque_val == 'indra_b3':
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 3'))
                        elif bloque_val in ('indra', 'indra_a'):
                            bloque_obj = bloque_cache.get(
                                normalize_text('bloque 4'))

                        grupo_resolutor_obj = None
                        if bloque_val == 'indra_b3':
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_3B'))
                        elif bloque_val in ('indra', 'indra_a'):
                            grupo_resolutor_obj = grupo_resolutor_cache.get(
                                normalize_text('SWF_INDRA_G3'))

                        impacto_obj = default_impacto
                        interfaz_obj = default_interfaz
                        usuario_asignado_obj = usuario_cache.get(
                            normalize_text(row['usuario_asignado_id']))
                        workaround_val = 'Sí' if 'con wa' in row['workaround'].strip(
                        ).lower() else 'No'

                        # <<<--- PASO 2: CAMBIAR update_or_create POR get_or_create ---<<<
                        obj, created = Incidencia.objects.get_or_create(
                            incidencia=incidencia_id,
                            defaults={
                                # ... todos tus campos ...
                                'descripcion_incidencia': row['descripcion_incidencia'].strip(),
                                'fecha_apertura': timezone.make_aware(datetime.strptime(row['fecha_apertura'].strip(), '%d-%m-%Y %H:%M:%S')) if row['fecha_apertura'].strip() else None,
                                'fecha_ultima_resolucion': timezone.make_aware(datetime.strptime(row['fecha_ultima_resolucion'].strip(), '%d-%m-%Y %H:%M:%S')) if row['fecha_ultima_resolucion'].strip() else None,
                                'causa': row['causa'].strip(),
                                'bitacora': row['bitacora'].strip(),
                                'tec_analisis': row['tec_analisis'].strip(),
                                'correccion': row['correccion'].strip(),
                                'solucion_final': row['solucion_final'].strip(),
                                'observaciones': row['observaciones'].strip(),
                                'demandas': row['demanadas'].strip(),
                                'workaround': workaround_val,
                                'aplicacion': aplicacion_obj,
                                'estado': estado_obj,
                                'severidad': severidad_obj,
                                'grupo_resolutor': grupo_resolutor_obj,
                                'interfaz': interfaz_obj,
                                'impacto': impacto_obj,
                                'cluster': cluster_obj,
                                'bloque': bloque_obj,
                                'codigo_cierre': codigo_cierre_obj,
                                'usuario_asignado': usuario_asignado_obj,
                            }
                        )

                        # <<<--- PASO 3: AJUSTAR LÓGICA DE CONTADORES Y LOGGING ---<<<
                        if created:
                            new_incidents_count += 1
                            logger.info(
                                f"Incidencia {incidencia_id} CREADA con éxito.")
                        else:
                            existing_skipped_count += 1  # <-- Usar nuevo contador
                            logger.info(
                                f"Incidencia {incidencia_id} ya existe, se omite.")

                    except Exception as e:
                        logger.error(
                            f"Error procesando fila {line_number} (Incidencia: {incidencia_id}): {e}", exc_info=True)
                        failed_rows.append({'line': line_number, 'row_data': ', '.join(
                            map(str, row.values)), 'error': str(e)})

            # <<<--- PASO 4: AJUSTAR RESUMEN FINAL ---<<<
            log_summary = f"""
            \n--------------------------------------------------
            \nRESUMEN DE CARGA MASIVA
            \nUsuario: {request.user}
            \nArchivo: {file.name}
            \n--------------------------------------------------
            \nTotal de filas leídas del archivo: {len(df)}
            \nIncidencias nuevas creadas: {new_incidents_count}
            \nIncidencias omitidas (por ya existir): {existing_skipped_count}
            \nIncidencias omitidas (por 'indra_d'): {skipped_indra_d_count}
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

            if new_incidents_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se crearon {new_incidents_count} incidencias nuevas.')
            if existing_skipped_count > 0:
                messages.info(
                    request, f'Se omitieron {existing_skipped_count} incidencias que ya existían.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Por favor, revisa los detalles.')
            if skipped_indra_d_count > 0:
                messages.info(
                    request, f'Se omitieron {skipped_indra_d_count} incidencias con valor "indra_d".')

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
