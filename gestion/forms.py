from django import forms
from datetime import timedelta
from .models import Aplicacion, ReglaSLA, HorarioLaboral, Usuario, Estado, GrupoResolutor, DiaFeriado


class UsuarioForm(forms.ModelForm):
    """
    Formulario para crear y editar instancias del modelo Usuario.
    """
    class Meta:
        model = Usuario
        fields = ['usuario', 'nombre', 'habilitado']
        widgets = {
            'usuario': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'habilitado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'usuario': 'Nombre de Usuario',
            'nombre': 'Nombre Completo',
        }


class EstadoForm(forms.ModelForm):
    """
    Formulario para crear y editar instancias del modelo Estado.
    """
    class Meta:
        model = Estado
        fields = ['desc_estado', 'uso_estado']
        widgets = {
            'desc_estado': forms.TextInput(attrs={'class': 'form-control'}),
            'uso_estado': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'desc_estado': 'Descripción del Estado',
        }


class GrupoResolutorForm(forms.ModelForm):
    """
    Formulario para crear y editar instancias del modelo GrupoResolutor.
    """
    class Meta:
        model = GrupoResolutor
        fields = ['desc_grupo_resol']
        widgets = {
            'desc_grupo_resol': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'desc_grupo_resol': 'Descripción del Grupo Resolutor',
        }


class AplicacionForm(forms.ModelForm):
    """
    Formulario para crear y editar instancias del modelo Aplicacion.
    """
    class Meta:
        model = Aplicacion
        # Se incluyen todos los campos del formulario de registro/edición
        fields = ['cod_aplicacion', 'nombre_aplicacion', 'bloque',
                  'criticidad', 'estado', 'desc_aplicacion']
        widgets = {
            'cod_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'bloque': forms.Select(attrs={'class': 'form-control'}),
            'criticidad': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'desc_aplicacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'cod_aplicacion': 'Código Aplicación',
            'nombre_aplicacion': 'Nombre de la Aplicación',
            'bloque': 'Bloque',
            'criticidad': 'Criticidad',
            'desc_aplicacion': 'Descripción',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra el queryset del campo 'estado' para mostrar solo los que
        # son de uso 'Aplicacion'.
        # Usamos la clase Choices del modelo para evitar errores de tipeo.
        self.fields['estado'].queryset = Estado.objects.filter(
            uso_estado=Estado.UsoChoices.APLICACION)

        # Mejora: Si no existen estados de tipo 'Aplicacion', se deshabilita el campo
        # para evitar errores y guiar al usuario.
        if not self.fields['estado'].queryset.exists():
            self.fields['estado'].disabled = True
            self.fields['estado'].required = False
            self.fields['estado'].help_text = 'No hay estados de tipo "Aplicacion" disponibles.'

        # Para replicar el comportamiento del HTML original, hacemos estos campos obligatorios
        # y añadimos un texto de 'placeholder' a los desplegables.
        self.fields['bloque'].required = True
        self.fields['criticidad'].required = True
        self.fields['estado'].required = True

        self.fields['bloque'].empty_label = "Seleccione..."
        self.fields['criticidad'].empty_label = "Seleccione..."
        self.fields['estado'].empty_label = "Seleccione..."


class ReglaSLAForm(forms.ModelForm):
    # 1. Creamos un campo personalizado para que el usuario ingrese las horas.
    #    Este campo no existe en el modelo, es solo para la interfaz.
    tiempo_en_horas = forms.DecimalField(
        label="Tiempo SLA (en horas)",
        required=True,
        min_value=0.1,
        help_text="Ingrese el tiempo en horas. Ej: 8 para 8 horas, 1.5 para 1 hora y 30 minutos.",
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'step': '0.1'})
    )

    class Meta:
        model = ReglaSLA
        # 2. Excluimos el campo 'tiempo_sla' original porque lo manejaremos manualmente.
        fields = ['severidad', 'criticidad_aplicacion']
        widgets = {
            'severidad': forms.Select(attrs={'class': 'form-control'}),
            'criticidad_aplicacion': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 3. Si estamos editando una regla existente, calculamos las horas
        #    a partir del 'tiempo_sla' guardado y poblamos nuestro campo personalizado.
        if self.instance and self.instance.pk and self.instance.tiempo_sla:
            total_seconds = self.instance.tiempo_sla.total_seconds()
            self.initial['tiempo_en_horas'] = round(total_seconds / 3600, 2)

        # Reordenamos los campos para una mejor experiencia de usuario
        self.order_fields(
            field_order=['tiempo_en_horas', 'criticidad_aplicacion', 'severidad'])

    def save(self, commit=True):
        # 4. Sobrescribimos el método save para realizar la conversión.
        instance = super().save(commit=False)
        horas = self.cleaned_data.get('tiempo_en_horas')
        instance.tiempo_sla = timedelta(hours=float(horas))
        if commit:
            instance.save()
        return instance


class DiaFeriadoForm(forms.ModelForm):
    """
    Formulario para crear y editar Días Feriados.
    """
    class Meta:
        model = DiaFeriado
        fields = ['fecha', 'descripcion']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'fecha': 'Fecha del Feriado',
            'descripcion': 'Descripción',
        }


class HorarioLaboralForm(forms.ModelForm):
    class Meta:
        model = HorarioLaboral
        fields = ['dia_semana', 'hora_inicio', 'hora_fin']
        widgets = {
            'dia_semana': forms.Select(attrs={'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Hacemos el campo 'dia_semana' de solo lectura en la edición
            self.fields['dia_semana'].widget.attrs['readonly'] = 'readonly'
            self.fields['dia_semana'].widget.attrs['disabled'] = 'disabled'
        else:
            # Para la creación, solo mostramos los días que aún no tienen un horario definido
            dias_existentes = HorarioLaboral.objects.values_list(
                'dia_semana', flat=True)
            opciones_disponibles = [
                choice for choice in self.fields['dia_semana'].choices if choice[0] not in dias_existentes]
            self.fields['dia_semana'].choices = opciones_disponibles
