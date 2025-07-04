# gestion/views/incidencias.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import Incidencia


@login_required
@no_cache
def incidencias_view(request):
    """Maneja la lógica para la página de gestión de incidencias."""
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de incidencias.")
    incidencias = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'criticidad', 'impacto'
    ).all()
    context = {'lista_de_incidencias': incidencias}
    return render(request, 'gestion/incidencia.html', context)
