from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallettransaction",
            name="gateway",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="wallettransaction",
            name="gateway_ref",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
