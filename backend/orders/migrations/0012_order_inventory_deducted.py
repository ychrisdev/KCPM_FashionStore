# DB có thể đã có cột inventory_deducted (NOT NULL) ngoài Django

from django.db import migrations, models


def _ensure_inventory_deducted_column(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as c:
        if conn.vendor == "postgresql":
            c.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'orders_order'
                  AND column_name = 'inventory_deducted'
                """
            )
            if c.fetchone():
                c.execute(
                    """
                    SELECT data_type FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'orders_order'
                      AND column_name = 'inventory_deducted'
                    """
                )
                row = c.fetchone()
                dt = (row[0] if row else "") or ""
                if dt in ("integer", "smallint", "bigint"):
                    c.execute(
                        "UPDATE orders_order SET inventory_deducted = 1 "
                        "WHERE inventory_deducted IS NULL"
                    )
                else:
                    c.execute(
                        "UPDATE orders_order SET inventory_deducted = TRUE "
                        "WHERE inventory_deducted IS NULL"
                    )
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN inventory_deducted boolean NOT NULL DEFAULT true"
            )
        elif conn.vendor == "sqlite":
            c.execute("PRAGMA table_info(orders_order)")
            if any(row[1] == "inventory_deducted" for row in c.fetchall()):
                return
            c.execute(
                "ALTER TABLE orders_order ADD COLUMN inventory_deducted bool NOT NULL DEFAULT 1"
            )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_gateway_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="order",
                    name="inventory_deducted",
                    field=models.BooleanField(
                        default=True,
                        help_text="Tồn kho đã trừ khi đặt hàng (checkout).",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(_ensure_inventory_deducted_column, _noop_reverse),
            ],
        ),
    ]
