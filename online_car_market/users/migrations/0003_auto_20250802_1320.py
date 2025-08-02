from django.db import migrations

def migrate_roles_to_groups(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Group = apps.get_model('auth', 'Group')  # historical Group model

    # Ensure all groups exist
    roles = ['super_admin', 'admin', 'sales', 'accounting', 'buyer', 'broker', 'dealer']
    role_groups = {}
    for role in roles:
        group, _ = Group.objects.get_or_create(name=role)
        role_groups[role] = group

    for user in User.objects.all():
        role = user.role
        if role == 'super_admin':
            user.is_superuser = True
            user.is_staff = True
            user.save()
        if role in role_groups:
            user.groups.add(role_groups[role])

def reverse_migration(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_options'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_to_groups, reverse_migration),
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
        migrations.RemoveField(
            model_name='user',
            name='permissions',
        ),
    ]

