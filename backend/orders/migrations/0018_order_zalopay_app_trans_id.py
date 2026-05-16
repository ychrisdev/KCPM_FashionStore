# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0017_alter_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="zalopay_app_trans_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=48,
            ),
        ),
    ]
