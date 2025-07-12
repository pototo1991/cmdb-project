# gestion/views/__init__.py

from .dashboard import dashboard_view
from .incidencias import incidencias_view, registrar_incidencia_view
from .aplicaciones import (aplicaciones_view, registrar_aplicacion_view,
                           eliminar_aplicacion_view, editar_aplicacion_view, carga_masiva_view)
from .cod_cierre import (
    codigos_cierre_view, registrar_cod_cierre_view, eliminar_cod_cierre_view, editar_cod_cierre_view, carga_masiva_cod_cierre_view)
from .logs import view_logs, download_log_file
