# DB có thể đã có cột gateway_status (NOT NULL) ngoài Django

from django.db import migrations, models


def _ensure_gateway_status_column(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as c:
        if conn.vendor == "postgresql":
            c.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'orders_order'
                  AND column_name = 'gateway_status'
                """
            )
            if c.fetchone():
                c.execute(
                    """
                    UPDATE orders_order
                    SET gateway_status = 'none'
                    WHERE gateway_status IS NULL OR TRIM(gateway_status::text) = ''
                    """
                )
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN gateway_status varchar(24) NOT NULL DEFAULT 'none'"
            )
        elif conn.vendor == "sqlite":
            c.execute("PRAGMA table_info(orders_order)")
            if any(row[1] == "gateway_status" for row in c.fetchall()):
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN gateway_status varchar(24) NOT NULL DEFAULT 'none'"
            )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_order_payment_method"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="order",
                    name="gateway_status",
                    field=models.CharField(
                        choices=(
                            ("none", "Không qua cổng (COD)"),
                            ("pending", "Chờ thanh toán"),
                            ("paid", "Đã thanh toán"),
                            ("failed", "Thanh toán thất bại"),
                        ),
                        default="none",
                        max_length=24,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(_ensure_gateway_status_column, _noop_reverse),
            ],
        ),
    ]
