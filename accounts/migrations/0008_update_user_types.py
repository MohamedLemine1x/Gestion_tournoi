from django.db import migrations

def update_user_types(apps, schema_editor):
    """
    Mise à jour des utilisateurs ayant le type 'invite' vers le type 'participant'
    """
    CustomUser = apps.get_model('accounts', 'CustomUser')
    # Mettre à jour tous les utilisateurs qui ont le type 'invite'
    CustomUser.objects.filter(type='invite').update(type='participant')

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_remove_unused_profile_fields'),  # Mise à jour avec la dernière migration
    ]

    operations = [
        migrations.RunPython(update_user_types),
    ] 