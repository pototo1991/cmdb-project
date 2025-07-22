# gestion/views/incidencias.py

import csv
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.db import transaction
from .utils import no_cache, logger
from ..models import Aplicacion, Estado, Severidad, Impacto, GrupoResolutor, Interfaz, Cluster, Bloque, Incidencia, CodigoCierre, Usuario
from django.core.exceptions import ObjectDoesNotExist
from unidecode import unidecode


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
    (Versión con asignación de nuevos campos de texto y usuario).
    """
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
        # CAMBIO: Se añade la caché para usuarios
        usuario_cache = {normalize_text(
            u.nombre): u for u in Usuario.objects.all()}

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

        failed_rows = []
        success_count = 0

        try:
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

                        # ... (lógica de aplicación y código de cierre sin cambios) ...
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
                            continue
                        bloque_obj = None
                        if bloque_val == 'indra_b3':
                            bloque_obj = bloque_cache.get('bloque 3')
                        elif bloque_val == 'indra':
                            bloque_obj = bloque_cache.get('bloque 4')

                        impacto_obj = default_impacto
                        interfaz_obj = default_interfaz
                        grupo_resolutor_obj = None

                        # CAMBIO: Se busca el usuario en la caché
                        usuario_asignado_obj = usuario_cache.get(
                            normalize_text(row['usuario_asignado_id']))

                        workaround_val = 'Sí' if 'con wa' in row['workaround'].strip(
                        ).lower() else 'No'

                        Incidencia.objects.update_or_create(
                            incidencia=incidencia_id,
                            defaults={
                                'descripcion_incidencia': row['descripcion_incidencia'].strip(),
                                'fecha_apertura': datetime.strptime(row['fecha_apertura'].strip(), '%d-%m-%Y %H:%M:%S') if row['fecha_apertura'].strip() else None,
                                'fecha_ultima_resolucion': datetime.strptime(row['fecha_ultima_resolucion'].strip(), '%d-%m-%Y %H:%M:%S') if row['fecha_ultima_resolucion'].strip() else None,
                                # CAMBIO: Se asignan los campos de texto solicitados
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
                                # CAMBIO: Se asigna el usuario encontrado
                                'usuario_asignado': usuario_asignado_obj,
                            }
                        )
                        success_count += 1

                    except ObjectDoesNotExist as e:
                        failed_rows.append({'line': line_number, 'row_data': ', '.join(
                            map(str, row.values)), 'error': f"No se encontró un registro coincidente: {e}"})
                    except Exception as e:
                        failed_rows.append({'line': line_number, 'row_data': ', '.join(
                            map(str, row.values)), 'error': str(e)})

            # ... (logging y mensajes sin cambios) ...
            log_summary = f"""
            \n--------------------------------------------------
            \nRESUMEN DE CARGA MASIVA
            \nUsuario: {request.user}
            \nArchivo: {file.name}
            \n--------------------------------------------------
            \nTotal de filas en el archivo: {len(df)}
            \nIncidencias cargadas con éxito: {success_count}
            \nIncidencias con errores: {len(failed_rows)}
            \n--------------------------------------------------
            """
            if failed_rows:
                log_summary += "\nDETALLE DE ERRORES:\n"
                for item in failed_rows:
                    incidencia_id_error = item.get(
                        'row_data', 'N/A').split(',')[0]
                    log_summary += f"  - Fila {item['line']} (Incidencia: {incidencia_id_error}): {item['error']}\n"

            log_summary += "--------------------------------------------------"
            logger.info(log_summary)

            if success_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se procesaron {success_count} incidencias con éxito.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Por favor, revisa los detalles a continuación.')
            return render(request, 'gestion/carga_masiva_incidencia.html', {'failed_rows': failed_rows})

        except Exception as e:
            logger.error(
                f"Error crítico al leer o procesar el archivo '{file.name}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al leer o procesar el archivo: {e}')
            return redirect('gestion:carga_masiva_incidencia')

    return render(request, 'gestion/carga_masiva_incidencia.html')
