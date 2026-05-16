from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_admin_enhancements"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscountCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("discount_percent", models.PositiveIntegerField()),
                ("min_order_value", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("usage_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("used_count", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ("-id",)},
        ),
        migrations.AddField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, help_text="So tien giam tu ma giam gia (VND)", max_digits=12),
        ),
        migrations.AddField(
            model_name="order",
            name="discount_code",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="orders.discountcode"),
        ),
        migrations.AddField(
            model_name="order",
            name="discount_code_snapshot",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
