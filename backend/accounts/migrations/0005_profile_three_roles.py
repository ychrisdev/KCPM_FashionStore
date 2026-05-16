# Generated manually — gộp role cũ thành customer / staff / admin

from django.db import migrations, models


def forwards_map_old_roles(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Profile.objects.filter(
        role__in=("product_manager", "order_manager", "customer_support")
    ).update(role="staff")


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_profile_avatar"),
    ]

    operations = [
        migrations.RunPython(forwards_map_old_roles, backwards_noop),
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("customer", "Customer"),
                    ("staff", "Staff"),
                    ("admin", "Admin"),
                ],
                default="customer",
                max_length=20,
            ),
        ),
    ]
