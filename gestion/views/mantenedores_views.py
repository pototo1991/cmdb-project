from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import ProtectedError
from ..models import Usuario, Estado, GrupoResolutor, ReglaSLA, DiaFeriado, HorarioLaboral
from datetime import timedelta
from ..forms import UsuarioForm, ReglaSLAForm, HorarioLaboralForm, EstadoForm, GrupoResolutorForm, DiaFeriadoForm


def mantenedores_main(request):
    """Página principal que muestra las tarjetas de los diferentes mantenedores."""
    return render(request, 'gestion/mantenedores/mantenedores_main.html')

# === Vistas para Usuarios ===


def listar_usuarios(request):
    """Muestra la lista de todos los usuarios."""
    registros = Usuario.objects.all().order_by('usuario')
    context = {
        'registros': registros,
    }
    return render(request, 'gestion/mantenedores/listar_usuarios.html', context)


def registrar_usuario(request):
    """Maneja la creación de un nuevo usuario."""
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gestion:listar_usuarios')
    else:
        form = UsuarioForm()

    context = {
        'form': form,
        'title': 'Agregar Usuario',
        'action_url': reverse_lazy('gestion:registrar_usuario')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_usuario(request, pk):
    """Maneja la edición de un usuario existente."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('gestion:listar_usuarios')
    else:
        form = UsuarioForm(instance=usuario)

    context = {
        'form': form,
        'title': 'Editar Usuario',
        'action_url': reverse_lazy('gestion:editar_usuario', kwargs={'pk': usuario.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_usuario(request, pk):
    """Elimina un usuario."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        # Aquí podrías añadir lógica para prevenir la eliminación si el usuario tiene incidencias, etc.
        usuario.delete()
    return redirect('gestion:listar_usuarios')


# === Vistas para Estados (Placeholder) ===
def listar_estados(request):
    """Muestra la lista de todos los estados."""
    registros = Estado.objects.all().order_by('desc_estado')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_estados.html', context)


def registrar_estado(request):
    """Maneja la creación de un nuevo estado."""
    if request.method == 'POST':
        form = EstadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El estado ha sido registrado correctamente.")
            return redirect('gestion:listar_estados')
    else:
        form = EstadoForm()

    context = {
        'form': form,
        'title': 'Agregar Estado',
        'action_url': reverse_lazy('gestion:registrar_estado')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_estado(request, pk):
    """Maneja la edición de un estado existente."""
    estado = get_object_or_404(Estado, pk=pk)
    if request.method == 'POST':
        form = EstadoForm(request.POST, instance=estado)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El estado ha sido actualizado correctamente.")
            return redirect('gestion:listar_estados')
    else:
        form = EstadoForm(instance=estado)

    context = {
        'form': form,
        'title': 'Editar Estado',
        'action_url': reverse_lazy('gestion:editar_estado', kwargs={'pk': estado.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_estado(request, pk):
    """Elimina un estado, con protección para evitar borrar registros en uso."""
    estado = get_object_or_404(Estado, pk=pk)
    if request.method == 'POST':
        try:
            estado_desc = estado.desc_estado
            estado.delete()
            messages.success(
                request, f"El estado '{estado_desc}' ha sido eliminado correctamente.")
        except ProtectedError:
            messages.error(
                request, f"No se puede eliminar el estado '{estado.desc_estado}' porque está en uso (ej. en Aplicaciones o Incidencias).")
    return redirect('gestion:listar_estados')

# === Vistas para Grupos Resolutores (Placeholder) ===


def listar_grupos(request):
    """Muestra la lista de todos los grupos resolutores."""
    registros = GrupoResolutor.objects.all().order_by('desc_grupo_resol')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_grupos.html', context)


def registrar_grupo(request):
    """Maneja la creación de un nuevo grupo resolutor."""
    if request.method == 'POST':
        form = GrupoResolutorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El grupo resolutor ha sido registrado correctamente.")
            return redirect('gestion:listar_grupos')
    else:
        form = GrupoResolutorForm()

    context = {
        'form': form,
        'title': 'Agregar Grupo Resolutor',
        'action_url': reverse_lazy('gestion:registrar_grupo')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_grupo(request, pk):
    """Maneja la edición de un grupo resolutor existente."""
    grupo = get_object_or_404(GrupoResolutor, pk=pk)
    if request.method == 'POST':
        form = GrupoResolutorForm(request.POST, instance=grupo)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El grupo resolutor ha sido actualizado correctamente.")
            return redirect('gestion:listar_grupos')
    else:
        form = GrupoResolutorForm(instance=grupo)

    context = {
        'form': form,
        'title': 'Editar Grupo Resolutor',
        'action_url': reverse_lazy('gestion:editar_grupo', kwargs={'pk': grupo.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_grupo(request, pk):
    """Elimina un grupo resolutor."""
    grupo = get_object_or_404(GrupoResolutor, pk=pk)
    if request.method == 'POST':
        grupo_desc = grupo.desc_grupo_resol
        grupo.delete()
        messages.success(
            request, f"El grupo resolutor '{grupo_desc}' ha sido eliminado correctamente.")
    return redirect('gestion:listar_grupos')

# ... y así sucesivamente para los otros mantenedores ...


def listar_reglas_sla(request):
    """Muestra la lista de todas las reglas de SLA."""
    # Usamos select_related para optimizar la consulta y evitar N+1 queries
    registros = ReglaSLA.objects.select_related(
        'severidad', 'criticidad_aplicacion').all()
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_reglas_sla.html', context)


def registrar_regla_sla(request):
    """Maneja la creación de una nueva regla de SLA."""
    if request.method == 'POST':
        form = ReglaSLAForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "La regla de SLA ha sido registrada correctamente.")
            return redirect('gestion:listar_reglas_sla')
    else:
        form = ReglaSLAForm()

    context = {
        'form': form,
        'title': 'Registrar Regla de SLA',
        'action_url': reverse_lazy('gestion:registrar_regla_sla')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_regla_sla(request, pk):
    """Maneja la edición de una regla de SLA existente."""
    regla = get_object_or_404(ReglaSLA, pk=pk)
    if request.method == 'POST':
        form = ReglaSLAForm(request.POST, instance=regla)
        if form.is_valid():
            form.save()
            messages.success(
                request, "La regla de SLA ha sido actualizada correctamente.")
            return redirect('gestion:listar_reglas_sla')
    else:
        form = ReglaSLAForm(instance=regla)

    context = {
        'form': form,
        'title': 'Editar Regla de SLA',
        'action_url': reverse_lazy('gestion:editar_regla_sla', kwargs={'pk': regla.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_regla_sla(request, pk):
    """Elimina una regla de SLA."""
    regla = get_object_or_404(ReglaSLA, pk=pk)
    if request.method == 'POST':
        regla_desc = str(regla)
        regla.delete()
        messages.success(
            request, f"La regla de SLA para '{regla_desc}' ha sido eliminada.")
    return redirect('gestion:listar_reglas_sla')


def listar_dias_feriados(request):
    """Muestra la lista de todos los días feriados."""
    registros = DiaFeriado.objects.all().order_by('fecha')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_dias_feriados.html', context)


def registrar_dia_feriado(request):
    """Maneja la creación de un nuevo día feriado."""
    if request.method == 'POST':
        form = DiaFeriadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El día feriado ha sido registrado correctamente.")
            return redirect('gestion:listar_dias_feriados')
    else:
        form = DiaFeriadoForm()

    context = {
        'form': form,
        'title': 'Agregar Día Feriado',
        'action_url': reverse_lazy('gestion:registrar_dia_feriado')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_dia_feriado(request, pk):
    """Maneja la edición de un día feriado existente."""
    feriado = get_object_or_404(DiaFeriado, pk=pk)
    if request.method == 'POST':
        form = DiaFeriadoForm(request.POST, instance=feriado)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El día feriado ha sido actualizado correctamente.")
            return redirect('gestion:listar_dias_feriados')
    else:
        form = DiaFeriadoForm(instance=feriado)

    context = {
        'form': form,
        'title': 'Editar Día Feriado',
        'action_url': reverse_lazy('gestion:editar_dia_feriado', kwargs={'pk': feriado.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_dia_feriado(request, pk):
    """Elimina un día feriado."""
    feriado = get_object_or_404(DiaFeriado, pk=pk)
    if request.method == 'POST':
        feriado_desc = f"{feriado.fecha.strftime('%d-%m-%Y')} - {feriado.descripcion}"
        feriado.delete()
        messages.success(
            request, f"El día feriado '{feriado_desc}' ha sido eliminado correctamente.")
    return redirect('gestion:listar_dias_feriados')


def listar_horarios_laborales(request):
    """
    Muestra la lista de todos los horarios laborales y determina si se pueden
    agregar nuevos (si no existen registros para los 7 días de la semana).
    """
    registros = HorarioLaboral.objects.all()
    se_pueden_agregar_mas = registros.count() < 7
    context = {
        'registros': registros,
        'se_pueden_agregar_mas': se_pueden_agregar_mas,
    }
    return render(request, 'gestion/mantenedores/listar_horarios_laborales.html', context)


def registrar_horario_laboral(request):
    """Maneja la creación de un nuevo horario laboral para un día de la semana faltante."""
    if request.method == 'POST':
        form = HorarioLaboralForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El nuevo horario laboral ha sido registrado correctamente.")
            return redirect('gestion:listar_horarios_laborales')
    else:
        form = HorarioLaboralForm()

    context = {
        'form': form,
        'title': 'Agregar Horario Laboral',
        'action_url': reverse_lazy('gestion:registrar_horario_laboral')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_horario_laboral(request, pk):
    """Maneja la edición de un horario laboral existente."""
    horario = get_object_or_404(HorarioLaboral, pk=pk)
    if request.method == 'POST':
        form = HorarioLaboralForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"El horario para el {horario.get_dia_semana_display()} ha sido actualizado correctamente.")
            return redirect('gestion:listar_horarios_laborales')
    else:
        form = HorarioLaboralForm(instance=horario)

    context = {
        'form': form,
        'title': f'Editar Horario para {horario.get_dia_semana_display()}',
        'action_url': reverse_lazy('gestion:editar_horario_laboral', kwargs={'pk': horario.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_horario_laboral(request, pk):
    """Elimina un horario laboral, permitiendo que se pueda volver a crear."""
    horario = get_object_or_404(HorarioLaboral, pk=pk)
    if request.method == 'POST':
        dia_semana_display = horario.get_dia_semana_display()
        horario.delete()
        messages.success(
            request, f"El horario para el {dia_semana_display} ha sido eliminado correctamente.")
    return redirect('gestion:listar_horarios_laborales')
