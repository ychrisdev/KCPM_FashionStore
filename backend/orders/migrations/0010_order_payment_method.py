# Generated manually — DB có thể đã có cột payment_method (NOT NULL) ngoài Django

from django.db import migrations, models


def _ensure_payment_method_column(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as c:
        if conn.vendor == "postgresql":
            c.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'orders_order'
                  AND column_name = 'payment_method'
                """
            )
            if c.fetchone():
                c.execute(
                    """
                    UPDATE orders_order
                    SET payment_method = 'cod'
                    WHERE payment_method IS NULL OR TRIM(payment_method::text) = ''
                    """
                )
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN payment_method varchar(24) NOT NULL DEFAULT 'cod'"
            )
        elif conn.vendor == "sqlite":
            c.execute("PRAGMA table_info(orders_order)")
            if any(row[1] == "payment_method" for row in c.fetchall()):
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN payment_method varchar(24) NOT NULL DEFAULT 'cod'"
            )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0009_order_completed_at"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="order",
                    name="payment_method",
                    field=models.CharField(
                        choices=(
                            ("cod", "Thanh toán khi nhận hàng (COD)"),
                            ("online", "Thanh toán trực tuyến"),
                        ),
                        default="cod",
                        max_length=24,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(_ensure_payment_method_column, _noop_reverse),
            ],
        ),
    ]
