# Bù khi DB thiếu cột feedback_type (ProgrammingError) dù django_migrations đã có 0003+.

from django.db import migrations


def _ensure_feedback_type(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE reviews_review ADD COLUMN IF NOT EXISTS "
                "feedback_type VARCHAR(20) NOT NULL DEFAULT 'quality'"
            )
        return
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(reviews_review)")
            cols = {row[1] for row in cursor.fetchall()}
            if "feedback_type" not in cols:
                cursor.execute(
                    "ALTER TABLE reviews_review ADD COLUMN feedback_type "
                    "VARCHAR(20) NOT NULL DEFAULT 'quality'"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0005_admin_enhancements"),
    ]

    operations = [
        migrations.RunPython(_ensure_feedback_type, migrations.RunPython.noop),
    ]
