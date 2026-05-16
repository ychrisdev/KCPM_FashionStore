# gateway_transaction_id + payment_method choices (cod / vnpay / momo)

from django.db import migrations, models


def forwards_online_to_cod(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(payment_method="online").update(payment_method="cod")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0012_order_inventory_deducted"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="gateway_transaction_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Mã giao dịch cổng (VNPay / MoMo)",
                max_length=128,
            ),
        ),
        migrations.RunPython(forwards_online_to_cod, noop_reverse),
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=(
                    ("cod", "Thanh toán khi nhận hàng (COD)"),
                    ("vnpay", "VNPay"),
                    ("momo", "Ví MoMo"),
                ),
                default="cod",
                max_length=24,
            ),
        ),
    ]
