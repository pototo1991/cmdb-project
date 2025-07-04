# gestion/views/dashboard.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import Incidencia  # '..' sube un nivel para encontrar models.py


@login_required
@no_cache
def dashboard_view(request):
    """Vista para el panel principal."""
    logger.info(f"El usuario '{request.user}' ha accedido al dashboard.")
    context = {
        'total_incidencias': Incidencia.objects.count(),
    }
    return render(request, 'gestion/dashboard.html', context)
