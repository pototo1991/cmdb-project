# gestion/views/logs.py

import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import no_cache, is_staff, logger


@login_required
@user_passes_test(is_staff)
@no_cache
def view_logs(request):
    """Muestra las últimas 800 líneas del archivo de log."""
    logger.info(
        f"El usuario staff '{request.user}' ha accedido al visor de logs.")
    log_file_path = settings.BASE_DIR / 'logs.log'
    log_content = ""
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()[-800:]
                log_content = ''.join(lines)
        except Exception as e:
            logger.error(
                f"Error al leer el archivo de log '{log_file_path}': {e}")
            log_content = f"Hubo un error al intentar leer el archivo de log: {e}"
    else:
        logger.warning(
            f"El archivo de log no fue encontrado en la ruta: {log_file_path}")
        log_content = "El archivo de log 'logs.log' no ha sido encontrado."
    context = {'log_content': log_content}
    return render(request, 'gestion/view_logs.html', context)


@login_required
@user_passes_test(is_staff)
@no_cache
def download_log_file(request):
    """Permite descargar el archivo de log completo."""
    log_file_path = settings.BASE_DIR / 'logs.log'
    logger.info(
        f"El usuario '{request.user}' ha solicitado la descarga del log completo.")
    if os.path.exists(log_file_path):
        return FileResponse(open(log_file_path, 'rb'), as_attachment=True, filename='logs.log')
    else:
        logger.error(
            f"Intento de descarga de un archivo de log inexistente en: {log_file_path}")
        raise Http404("El archivo de log no fue encontrado.")
