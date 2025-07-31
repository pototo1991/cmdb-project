# gestion/views/calculo_sla.py

import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, time, timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .utils import logger
from ..models import Incidencia, ReglaSLA, HorarioLaboral, DiaFeriado, Usuario

# --- El resto del archivo permanece sin cambios hasta la vista de exportación ---
# (Se omiten las funciones de normalizar, parsear, etc. para brevedad)


def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = re.sub(r'\s+', ' ', texto).strip().lower()
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def parsear_bitacora(bitacora_texto, incidencia_id="N/A"):
    if not bitacora_texto:
        return []
    bitacora_texto_limpia = bitacora_texto.replace('¶', '\n')
    entries = []
    regex = re.compile(
        r'(\d{2}[-/]\d{2}[-/]\d{4} \d{1,2}:\d{2}:\d{2})\s*,\s*([^,]+?)\s*,\s*(.*?)(?=\s*[\r\n]+\s*\d{2}[-/]\d{2}[-/]\d{4}|\Z)', re.DOTALL)
    matches = regex.finditer(bitacora_texto_limpia)
    for match in matches:
        date_str, user_raw, message = match.groups()
        try:
            dt_obj_naive = datetime.strptime(
                date_str.replace('/', '-').strip(), "%d-%m-%Y %H:%M:%S")
            dt_obj_aware = timezone.make_aware(dt_obj_naive)
            entries.append({"fecha_hora": dt_obj_aware, "usuario": normalizar_texto(
                user_raw), "mensaje": message.strip()})
        except ValueError:
            logger.warning(
                f"Error parseando fecha en bitácora para Incidencia ID {incidencia_id}: '{date_str}'. Ignorando entrada.")
    entries.sort(key=lambda x: x["fecha_hora"])
    return entries


def is_working_time(dt_obj, horario_laboral, dias_feriados):
    """
    Verifica si una fecha y hora específicas caen dentro del horario laboral,
    excluyendo días feriados.
    """
    if dt_obj.date() in dias_feriados:
        return False

    dia_semana = dt_obj.weekday()
    horario_dia = horario_laboral.get(dia_semana)

    # CORRECCIÓN: Se verifica no solo si el horario existe, sino también si contiene horas válidas (no None).
    # Si 'horario_dia' es (None, None), 'horario_dia[0]' será None y la condición será verdadera, retornando False.
    if not horario_dia or not horario_dia[0]:
        return False

    hora_inicio, hora_fin = horario_dia
    return hora_inicio <= dt_obj.time() <= hora_fin


def calcular_tiempo_efectivo(start_dt, end_dt, horario_laboral, dias_feriados, es_critica_24_7=False):
    """
    Calcula el tiempo transcurrido entre dos fechas, contando solo el tiempo
    dentro del horario laboral (a menos que sea 24/7), con precisión de segundos.
    """
    if start_dt >= end_dt:
        return timedelta(0)

    # Si la incidencia es crítica, el cálculo es directo y ya tiene precisión de segundos.
    if es_critica_24_7:
        return end_dt - start_dt

    tiempo_laboral_total = timedelta(0)
    puntero_tiempo = start_dt

    # Itera segundo a segundo entre el inicio y el fin del segmento.
    while puntero_tiempo < end_dt:
        # Verifica si el segundo actual está dentro del horario laboral.
        if is_working_time(puntero_tiempo, horario_laboral, dias_feriados):
            tiempo_laboral_total += timedelta(seconds=1)

        # Avanza al siguiente segundo.
        puntero_tiempo += timedelta(seconds=1)

    return tiempo_laboral_total
# >>> FIN DE LA FUNCIÓN MODIFICADA <<<


def _timedelta_to_hms(td):
    if not td:
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def calcular_sla_desde_bitacora(incidencia, gestores_norm, horarios, feriados, reglas_sla):
    # VALIDACIÓN DE PRIORIDAD 1: Excluir incidencias que no aplican para SLA.
    # Esta validación se mueve al principio para que tenga la máxima prioridad.
    # Bloque ID 5 = 'Sin bloque'
    # Grupo Resolutor ID 15 = 'INDRA_D'
    if incidencia.bloque_id == 5 or incidencia.grupo_resolutor_id == 15:
        motivos = []
        if incidencia.bloque_id == 5:
            motivos.append("el bloque es 'Sin Bloque' (ID 5)")
        if incidencia.grupo_resolutor_id == 15:
            motivos.append("el grupo resolutor es 'INDRA_D' (ID 15)")

        razon_log = " y ".join(motivos)
        logger.info(
            f"Cálculo de SLA para Incidencia ID {incidencia.id} ('{incidencia.incidencia}') omitido porque {razon_log}."
        )
        return {"cumple_sla": "No Aplica"}

    # El resto de esta función y las vistas no necesitan cambios, ya que
    # la modificación está contenida dentro de 'calcular_tiempo_efectivo'.
    campos_faltantes = []
    if not incidencia.severidad:
        campos_faltantes.append("Severidad")
    if not incidencia.aplicacion:
        campos_faltantes.append("Aplicación")
    elif not incidencia.aplicacion.criticidad:
        campos_faltantes.append("Criticidad de la Aplicación")

    if campos_faltantes:
        mensaje_error = ", ".join(campos_faltantes)
        logger.warning(
            f"Cálculo de SLA para Incidencia ID {incidencia.id} ('{incidencia.incidencia}') omitido. Faltan datos: {mensaje_error}.")
        return {"cumple_sla": "No Calculado (Faltan Datos)"}

    logger.info(
        f"\n--- Analizando Segmentos para Incidencia: {incidencia.incidencia} ---")
    bitacora_entries = parsear_bitacora(incidencia.bitacora, incidencia.id)
    severidad_norm = normalizar_texto(incidencia.severidad.desc_severidad)
    es_critica_24_7 = (severidad_norm == "critica")
    tiempo_gestion_total = timedelta(0)

    if len(bitacora_entries) > 1:
        for i in range(len(bitacora_entries) - 1):
            entrada_actual, entrada_siguiente = bitacora_entries[i], bitacora_entries[i+1]
            start_user, end_user = entrada_actual['usuario'], entrada_siguiente['usuario']
            segment_start_str, segment_end_str = entrada_actual['fecha_hora'].strftime(
                '%d-%m-%Y %H:%M:%S'), entrada_siguiente['fecha_hora'].strftime('%d-%m-%Y %H:%M:%S')

            logger.info(f"Desde {segment_start_str} hasta {segment_end_str}.")
            logger.info(f"-> De: '{start_user}' | A: '{end_user}'")

            es_respuesta_de_gestor = end_user in gestores_norm
            reloj_no_pausado = 'pendiente' not in normalizar_texto(
                entrada_actual['mensaje'])

            if es_respuesta_de_gestor and reloj_no_pausado:
                tiempo_segmento = calcular_tiempo_efectivo(
                    entrada_actual["fecha_hora"], entrada_siguiente["fecha_hora"], horarios, feriados, es_critica_24_7)
                tiempo_gestion_total += tiempo_segmento
                logger.info(
                    f"✅ ANÁLISIS: Se cuenta el tiempo. Gestor '{end_user}' respondió. Tiempo sumado: {_timedelta_to_hms(tiempo_segmento)}")
            else:
                if not es_respuesta_de_gestor:
                    logger.info(
                        f"❌ ANÁLISIS: No se cuenta. El usuario '{end_user}' no es un gestor.")
                elif not reloj_no_pausado:
                    logger.info(
                        f"⏸️ ANÁLISIS: No se cuenta. El reloj está pausado por nota 'Pendiente' de '{start_user}'.")
            logger.info("-" * 60)

    if tiempo_gestion_total == timedelta(0) and not es_critica_24_7 and bitacora_entries:
        tiempo_gestion_total = timedelta(minutes=20)
        logger.info(
            "-> Aplicando fallback de 20 minutos por tiempo de gestión 0.")

    logger.info(
        f"-> TIEMPO TOTAL DE GESTIÓN PARA {incidencia.incidencia}: {_timedelta_to_hms(tiempo_gestion_total)}\n")

    clave_regla = (incidencia.severidad.id,
                   incidencia.aplicacion.criticidad.id)
    tiempo_sla_objetivo = reglas_sla.get(clave_regla)
    cumple_sla = "SLA No Definido"
    if tiempo_sla_objetivo:
        cumple_sla = "Sí" if tiempo_gestion_total <= tiempo_sla_objetivo else "No"
    elif not bitacora_entries:
        cumple_sla = "No Calculado (Bitácora Vacía)"

    ultimo_gestor = "N/A"
    for entry in reversed(bitacora_entries):
        if entry["usuario"] in gestores_norm:
            ultimo_gestor = entry["usuario"]
            break

    return {"incidencia": incidencia, "tiempo_gestion_calculado": tiempo_gestion_total, "tiempo_gestion_horas": _timedelta_to_hms(tiempo_gestion_total), "sla_objetivo": tiempo_sla_objetivo, "sla_objetivo_horas": _timedelta_to_hms(tiempo_sla_objetivo), "cumple_sla": cumple_sla, "ultimo_gestor": ultimo_gestor}


@require_POST
def calcular_sla_view(request):
    try:
        data = json.loads(request.body)
        incidencia_ids = data.get('incidencia_ids', [])
        if not incidencia_ids:
            return JsonResponse({'status': 'error', 'message': 'No se seleccionaron incidencias.'}, status=400)

        incidencias_a_procesar = Incidencia.objects.filter(
            id__in=incidencia_ids).select_related('aplicacion__criticidad', 'severidad')
        gestores_norm = set(normalizar_texto(u.usuario)
                            for u in Usuario.objects.all())
        horarios = {h.dia_semana: (h.hora_inicio, h.hora_fin)
                    for h in HorarioLaboral.objects.all()}
        feriados = set(d.fecha for d in DiaFeriado.objects.all())
        reglas_sla = {(r.severidad_id, r.criticidad_aplicacion_id)                      : r.tiempo_sla for r in ReglaSLA.objects.all()}

        stats = Counter()
        resultados_vista = []
        for inc in incidencias_a_procesar:
            resultado = calcular_sla_desde_bitacora(
                inc, gestores_norm, horarios, feriados, reglas_sla)
            stats[resultado.get("cumple_sla", "Error")] += 1

            inc.tiempo_sla_calculado = resultado.get(
                "tiempo_gestion_calculado")
            inc.cumple_sla = resultado.get("cumple_sla", "Error")
            inc.save(update_fields=['tiempo_sla_calculado', 'cumple_sla'])
            resultados_vista.append({'id': inc.id, 'incidencia': inc.incidencia,
                                    'cumple_sla': inc.cumple_sla, 'tiempo_sla': resultado.get("tiempo_gestion_horas")})

        logger.info(
            "\n--- RESUMEN DE ESTADÍSTICAS DE SLA (Cálculo desde Tabla) ---")
        for estado, count in stats.items():
            logger.info(f"{estado:<40} : {count}")
        logger.info(
            f"{'Total de incidencias procesadas':<40} : {len(incidencias_a_procesar)}")
        logger.info(
            "----------------------------------------------------------\n")

        return JsonResponse({'status': 'success', 'message': f'Se procesaron {len(resultados_vista)} incidencias.', 'results': resultados_vista})
    except Exception as e:
        logger.error(
            f"Error en la vista calcular_sla_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Ocurrió un error inesperado.'}, status=500)


def exportar_sla_csv_view(request):
    gestores_norm = set(normalizar_texto(u.usuario)
                        for u in Usuario.objects.all())
    horarios = {h.dia_semana: (h.hora_inicio, h.hora_fin)
                for h in HorarioLaboral.objects.all()}
    feriados = set(d.fecha for d in DiaFeriado.objects.all())
    reglas_sla = {(r.severidad_id, r.criticidad_aplicacion_id)                  : r.tiempo_sla for r in ReglaSLA.objects.all()}

    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion__criticidad', 'severidad', 'usuario_asignado').all()

    # >>> INICIO DE LA CORRECCIÓN <<<
    # Se añade la lógica para procesar todos los filtros que vienen de la URL

    filtro_incidencia = request.GET.get('incidencia')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')

    if filtro_incidencia:
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)

    if filtro_fecha_desde:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            # Hacemos la fecha consciente de la zona horaria
            fecha_aware = timezone.make_aware(
                fecha_obj, timezone.get_default_timezone())
            # Filtramos por fecha_ultima_resolucion mayor o igual que la fecha de inicio
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_aware)
        except (ValueError, TypeError):
            pass  # Ignora el filtro si la fecha es inválida

    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            # Añadimos un día para incluir todo el día de la fecha "hasta"
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            fecha_aware = timezone.make_aware(
                fecha_obj_fin_dia, timezone.get_default_timezone())
            # Filtramos por fecha_ultima_resolucion menor que el día siguiente
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_aware)
        except (ValueError, TypeError):
            pass  # Ignora el filtro si la fecha es inválida

    # >>> FIN DE LA CORRECCIÓN <<<

    response = HttpResponse(content_type='text/csv', headers={
                            'Content-Disposition': 'attachment; filename="reporte_sla_bitacora.csv"'})
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['Incidencia', 'Fecha Resolucion', 'Ultimo Gestor', 'Aplicativo', 'Criticidad Aplicativo',
                    'Severidad', 'SLA Objetivo (Horas)', 'Tiempo Gestion (Horas)', 'Cumple SLA'])

    stats = Counter()
    for inc in incidencias_qs:
        resultado = calcular_sla_desde_bitacora(
            inc, gestores_norm, horarios, feriados, reglas_sla)
        stats[resultado.get("cumple_sla", "Error")] += 1

        if "Error" not in resultado.get("cumple_sla", ""):
            writer.writerow([
                inc.incidencia,
                inc.fecha_ultima_resolucion.strftime(
                    '%Y-%m-%d %H:%M:%S') if inc.fecha_ultima_resolucion else "N/A",
                resultado.get("ultimo_gestor", "N/A"),
                inc.aplicacion.nombre_aplicacion if inc.aplicacion else "N/A",
                inc.aplicacion.criticidad.desc_criticidad if inc.aplicacion and inc.aplicacion.criticidad else "N/A",
                inc.severidad.desc_severidad if inc.severidad else "N/A",
                resultado.get("sla_objetivo_horas", "N/A"),
                resultado.get("tiempo_gestion_horas", "N/A"),
                resultado.get("cumple_sla", "Error")
            ])

    logger.info("\n--- RESUMEN DE ESTADÍSTICAS DE SLA (Exportación CSV) ---")
    for estado, count in stats.items():
        logger.info(f"{estado:<40} : {count}")
    logger.info(
        # Usamos list() para obtener el conteo después de filtrar
        f"{'Total de incidencias procesadas':<40} : {len(list(incidencias_qs))}")
    logger.info("------------------------------------------------------\n")

    # Se establece una cookie que el JavaScript usará para saber que la descarga ha finalizado.
    response.set_cookie('descargaFinalizada', 'true', max_age=20, path='/')

    return response
