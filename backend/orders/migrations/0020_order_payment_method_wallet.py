# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0018_order_zalopay_app_trans_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cod", "Thanh toán khi nhận hàng (COD)"),
                    ("wallet", "Ví trên ứng dụng"),
                    ("vnpay", "VNPay"),
                    ("momo", "Ví MoMo"),
                    ("zalopay", "Ví ZaloPay"),
                ],
                default="cod",
                max_length=24,
            ),
        ),
    ]
