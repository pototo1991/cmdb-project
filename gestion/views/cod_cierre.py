# gestion/views/cod_cierre.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import CodigoCierre


@login_required
@no_cache
def codigos_cierre_view(request):
    """Muestra la lista de Códigos de Cierre."""
    logger.info(
        f"El usuario '{request.user}' está viendo la lista de códigos de cierre.")
    codigos = CodigoCierre.objects.select_related('aplicacion').all()
    context = {'lista_de_codigos': codigos}
    return render(request, 'gestion/cod_cierre.html', context)
