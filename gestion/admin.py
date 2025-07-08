from django.contrib import admin
from .models import (
    Bloque,
    Cluster,
    Criticidad,
    GrupoResolutor,
    Impacto,
    Estado,
    Interfaz,
    Aplicacion,
    CodigoCierre,
    Incidencia,
    Severidad,  # 1. Importamos el nuevo modelo Severidad
)

# Registros simples para los modelos de catálogo
admin.site.register(Bloque)
admin.site.register(Cluster)
admin.site.register(Criticidad)
admin.site.register(GrupoResolutor)
admin.site.register(Impacto)
admin.site.register(Estado)
admin.site.register(Interfaz)
# 2. Registramos Severidad para que aparezca en el admin
admin.site.register(Severidad)

# Registros personalizados para una mejor experiencia en el admin


@admin.register(Aplicacion)
class AplicacionAdmin(admin.ModelAdmin):
    # No se toca esta clase, ya que Aplicacion todavía tiene el campo criticidad
    list_display = ('cod_aplicacion', 'nombre_aplicacion',
                    'bloque', 'criticidad', 'estado')
    list_filter = ('bloque', 'criticidad', 'estado')
    search_fields = ('cod_aplicacion', 'nombre_aplicacion')


@admin.register(CodigoCierre)
class CodigoCierreAdmin(admin.ModelAdmin):
    list_display = ('cod_cierre', 'desc_cod_cierre', 'aplicacion')
    list_filter = ('aplicacion',)
    search_fields = ('cod_cierre', 'desc_cod_cierre')


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    # 3. Reemplazamos 'criticidad' por 'severidad'
    list_display = ('incidencia', 'aplicacion', 'estado',
                    'severidad', 'fecha_apertura', 'usuario_asignado')
    # 4. Reemplazamos 'criticidad' por 'severidad'
    list_filter = ('estado', 'severidad', 'aplicacion',
                   'grupo_resolutor', 'bloque')
    search_fields = ('incidencia', 'descripcion_incidencia',
                     'usuario_asignado')
    date_hierarchy = 'fecha_apertura'
    ordering = ('-fecha_apertura',)
