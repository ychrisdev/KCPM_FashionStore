"""
Đặt lại sequence PostgreSQL cho bảng products_product (và productimage).
Chạy khi gặp lỗi: duplicate key value violates unique constraint "products_product_pkey"
Lệnh: python manage.py reset_product_sequence
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Đặt lại sequence id của bảng products_product (PostgreSQL) để tránh lỗi duplicate key'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Bảng products_product
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('products_product', 'id'),
                    COALESCE((SELECT MAX(id) FROM products_product), 1)
                );
            """)
            self.stdout.write(self.style.SUCCESS('Sequence products_product.id reset OK'))

            # products_productimage
            try:
                cursor.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('products_productimage', 'id'),
                        COALESCE((SELECT MAX(id) FROM products_productimage), 1)
                    );
                """)
                self.stdout.write(self.style.SUCCESS('Sequence products_productimage.id reset OK'))
            except Exception as e:
                self.stdout.write(self.style.WARNING('products_productimage: %s' % str(e)))

        self.stdout.write(self.style.SUCCESS('Done. Try adding a product again.'))
