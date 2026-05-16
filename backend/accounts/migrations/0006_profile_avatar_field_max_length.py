# Generated manually — Facebook/Google ảnh đại diện là URL dài; ImageField mặc định max_length=100.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_profile_three_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="avatar",
            field=models.ImageField(
                blank=True,
                max_length=1024,
                null=True,
                upload_to="avatars/",
            ),
        ),
    ]
