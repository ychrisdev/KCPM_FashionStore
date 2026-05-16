"""Compare orders_order table columns to Order model (detect schema drift)."""

from django.core.management.base import BaseCommand
from django.db import connection

from orders.models import Order


class Command(BaseCommand):
    help = "List DB columns on orders_order missing from Order model (NOT NULL often breaks checkout)."

    def handle(self, *args, **options):
        model_cols = {f.column for f in Order._meta.concrete_fields}
        meta = {}

        with connection.cursor() as c:
            if connection.vendor == "postgresql":
                c.execute(
                    """
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'orders_order'
                    ORDER BY ordinal_position
                    """
                )
                for name, nullable, dtype in c.fetchall():
                    meta[name] = (nullable, dtype)
            elif connection.vendor == "sqlite":
                c.execute("PRAGMA table_info(orders_order)")
                for _cid, name, ctype, notnull, _dflt, _pk in c.fetchall():
                    meta[name] = ("NO" if notnull else "YES", ctype or "numeric")
            else:
                self.stdout.write(self.style.ERROR("Only PostgreSQL and SQLite are supported."))
                return

        db_cols = set(meta.keys())
        extra = sorted(db_cols - model_cols)

        if not extra:
            self.stdout.write(self.style.SUCCESS("OK: no extra columns vs Order model."))
            return

        self.stdout.write(
            self.style.WARNING(
                "Extra columns in DB (add fields + migrations if NOT NULL):\n"
            )
        )
        for name in extra:
            null, dtype = meta.get(name, ("?", "?"))
            self.stdout.write(f"  - {name}  ({dtype}, nullable={null})")
