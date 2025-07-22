from django.db import migrations


def add_initial_users(apps, schema_editor):
    """
    Añade una lista de usuarios iniciales a la tabla Usuario.
    """
    Usuario = apps.get_model('gestion', 'Usuario')
    usuarios_a_crear = [
        'ind_bllacc', 'ind_dcorra', 'ind_msalas', 'ind_smunoz', 'ind_jecocp',
        'ind_wsilva', 'ind_rarane', 'ind_camaga', 'ind_caranc', 'ind_ojagar'
    ]

    for username in usuarios_a_crear:
        # Como el campo 'nombre' es obligatorio, generamos uno a partir del 'usuario'.
        # Por ejemplo, de 'ind_wsilva' se generará 'Wsilva'.
        nombre_generado = username.replace('ind_', '').capitalize()
        Usuario.objects.update_or_create(
            usuario=username,
            defaults={'nombre': nombre_generado}
        )


class Migration(migrations.Migration):

    dependencies = [
        # Asegúrate que esta es tu última migración.
        ('gestion', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_initial_users),
    ]
