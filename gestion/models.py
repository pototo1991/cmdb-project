from django.db import models

# Modelos de tablas catálogo (simples)


class Bloque(models.Model):
    desc_bloque = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.desc_bloque


class Cluster(models.Model):
    desc_cluster = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.desc_cluster


class Criticidad(models.Model):
    desc_criticidad = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.desc_criticidad


class Severidad(models.Model):
    desc_severidad = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.desc_severidad


class GrupoResolutor(models.Model):
    desc_grupo_resol = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.desc_grupo_resol


class Impacto(models.Model):
    desc_impacto = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.desc_impacto


class Estado(models.Model):
    desc_estado = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.desc_estado


class Interfaz(models.Model):
    desc_interfaz = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.desc_interfaz

# Modelos con relaciones


class Aplicacion(models.Model):
    cod_aplicacion = models.CharField(max_length=50, unique=True)
    nombre_aplicacion = models.CharField(max_length=255)
    desc_aplicacion = models.TextField(blank=True, null=True)

    # Relaciones
    bloque = models.ForeignKey(
        Bloque, on_delete=models.PROTECT, null=True, blank=True)
    criticidad = models.ForeignKey(
        Criticidad, on_delete=models.PROTECT, null=True, blank=True)
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.cod_aplicacion} - {self.nombre_aplicacion}"


class CodigoCierre(models.Model):
    cod_cierre = models.CharField(max_length=50, unique=True)
    desc_cod_cierre = models.CharField(max_length=255, blank=True, null=True)
    causa_cierre = models.TextField(blank=True, null=True)

    # Relación
    aplicacion = models.ForeignKey(
        Aplicacion, on_delete=models.CASCADE, related_name='codigos_cierre')

    def __str__(self):
        return self.cod_cierre


class Incidencia(models.Model):
    # El ID automático será creado por Django.
    incidencia = models.CharField(max_length=50, unique=True)

    # Campos de texto y fecha
    descripcion_incidencia = models.TextField(blank=True)

    fecha_apertura = models.DateTimeField(null=True, blank=True)
    fecha_ultima_resolucion = models.DateTimeField(null=True, blank=True)

    causa = models.TextField(blank=True)
    bitacora = models.TextField(blank=True)
    tec_analisis = models.TextField(blank=True)
    correccion = models.TextField(blank=True)
    solucion_final = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    # usuario_asignado = models.CharField(max_length=150, blank=True)  # Campo eliminado

    demandas = models.TextField(blank=True)

    WORKAROUND_CHOICES = [
        ('No', 'No'),
        ('Sí', 'Sí'),
    ]
    workaround = models.CharField(
        max_length=2, choices=WORKAROUND_CHOICES, default='No')

    # Relaciones (ForeignKey)
    aplicacion = models.ForeignKey(
        Aplicacion,
        on_delete=models.CASCADE,
        related_name='incidencias',
        null=True,  # <-- AÑADIR ESTO
        blank=True  # <-- Y ESTO
    )
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, related_name='incidencias'
    )
    severidad = models.ForeignKey(
        Severidad,
        on_delete=models.PROTECT,
        related_name='incidencias',
        null=True,
        blank=True
    )
    grupo_resolutor = models.ForeignKey(
        GrupoResolutor, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_resueltas'
    )
    interfaz = models.ForeignKey(
        Interfaz, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    impacto = models.ForeignKey(
        Impacto, on_delete=models.PROTECT, related_name='incidencias'
    )
    cluster = models.ForeignKey(
        Cluster, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    bloque = models.ForeignKey(
        Bloque,
        on_delete=models.PROTECT,
        related_name='incidencias',
        null=True,  # <-- AÑADIR ESTO
        blank=True  # <-- Y ESTO
    )
    codigo_cierre = models.ForeignKey(
        CodigoCierre, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    usuario_asignado = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_asignadas'
    )

    def __str__(self):
        return self.incidencia

    class Meta:
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering = ['-fecha_apertura']


class Usuario(models.Model):
    # Django añade automáticamente un campo 'id' que es una clave primaria auto-incremental.
    # El nombre de la tabla en la base de datos será 'gestion_usuario' por defecto.
    usuario = models.CharField(max_length=150, unique=True)
    nombre = models.CharField(max_length=255)

    def __str__(self):
        return self.usuario
