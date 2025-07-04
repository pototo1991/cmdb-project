# gestion/views/aplicaciones.py

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
    context = {'lista_de_aplicaciones': aplicaciones}
    return render(request, 'gestion/aplicaciones.html', context)
