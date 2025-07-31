# gestion/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'gestion'

urlpatterns = [
    # Le decimos a LoginView que use tu plantilla 'home.html'
    path('', auth_views.LoginView.as_view(
        template_name='gestion/home.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='gestion:login'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logs/', views.view_logs, name='view_logs'),
    path('logs/download/', views.download_log_file, name='download_log'),
    path('aplicaciones/', views.aplicaciones_view, name='aplicaciones'),

    path('aplicaciones/registrar/', views.registrar_aplicacion_view,
         name='registrar_aplicacion'),
    path('aplicaciones/eliminar/<int:pk>/',
         views.eliminar_aplicacion_view, name='eliminar_aplicacion'),
    path('aplicaciones/editar/<int:pk>/',
         views.editar_aplicacion_view, name='editar_aplicacion'),
    path('aplicaciones/cargar/', views.carga_masiva_view,
         name='carga_masiva_aplicaciones'),

    path('codigos-cierre/', views.codigos_cierre_view, name='codigos_cierre'),
    path('codigos-cierre/registrar/', views.registrar_cod_cierre_view,
         name='registrar_cod_cierre'),
    path('codigos-cierre/eliminar/<int:pk>/',
         views.eliminar_cod_cierre_view, name='eliminar_cod_cierre'),
    path('codigos-cierre/editar/<int:pk>/',
         views.editar_cod_cierre_view, name='editar_cod_cierre'),
    path('codigos-cierre/cargar/', views.carga_masiva_cod_cierre_view,
         name='carga_masiva_cod_cierre'),
    path('ajax/get-ultimos-codigos-cierre/<int:aplicacion_id>/',
         views.obtener_ultimos_codigos_cierre, name='get_ultimos_codigos_cierre'),

    path('incidencias/', views.incidencias_view, name='incidencias'),
    path('incidencias/registrar/', views.registrar_incidencia_view,
         name='registrar_incidencia'),
    path('ajax/get-codigos-cierre/<int:aplicacion_id>/',
         views.get_codigos_cierre_por_aplicacion, name='get_codigos_cierre_por_aplicacion'),
    path('incidencias/editar/<int:pk>/',
         views.editar_incidencia_view, name='editar_incidencia'),
    path('incidencias/eliminar/<int:pk>/',
         views.eliminar_incidencia_view, name='eliminar_incidencia'),
    path('incidencias/carga-masiva/', views.carga_masiva_incidencia_view,
         name='carga_masiva_incidencia'),

    path('incidencias/calcular-sla/',
         views.calculo_sla.calcular_sla_view, name='calcular_sla'),
    path('incidencias/exportar-sla-csv/',
         views.exportar_sla_csv_view, name='exportar_sla_csv'),
    path('incidencias/exportar-reporte/', views.exportar_incidencias_reporte_view,
         name='exportar_incidencias_reporte'),

    # Nuevas rutas para la página de gráficos y su endpoint de datos
    path('graficos/', views.graficos_view, name='graficos'),
    path('graficos/data/', views.graficos_data_json, name='graficos_data_json'),
    path('ajax/get-codigos-cierre-graficos/',
         views.get_codigos_cierre_ajax, name='get_codigos_cierre_graficos'),

]
