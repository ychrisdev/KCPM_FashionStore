# Generated manually for birthday reminder feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_profile_avatar_field_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='birthday_reminder_sent_for_year',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
