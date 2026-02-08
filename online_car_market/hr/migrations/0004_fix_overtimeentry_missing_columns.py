from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0003_fix_overtimeentry_approved'),
    ]

    operations = [
        migrations.AddField(
            model_name='overtimeentry',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='overtimeentry',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]

