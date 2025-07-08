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
    path('incidencias/', views.incidencias_view, name='incidencias'),
    path('aplicaciones/', views.aplicaciones_view, name='aplicaciones'),
    path('codigos-cierre/', views.codigos_cierre_view, name='codigos_cierre'),
    path('aplicaciones/registrar/', views.registrar_aplicacion_view,
         name='registrar_aplicacion'),
    path('aplicaciones/eliminar/<int:pk>/',
         views.eliminar_aplicacion_view, name='eliminar_aplicacion'),
    path('aplicaciones/editar/<int:pk>/',
         views.editar_aplicacion_view, name='editar_aplicacion'),
    path('aplicaciones/cargar/', views.carga_masiva_view,
         name='carga_masiva_aplicaciones'),
]
