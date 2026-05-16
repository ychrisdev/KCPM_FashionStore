"""
Lệnh reset và tạo dữ liệu mẫu với ID hợp lý.
Chạy: python manage.py reset_products_data
"""
import io
import sys
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from products.models import Category, Promotion, Product, ProductImage, Color, Size, ProductVariant


class Command(BaseCommand):
    help = 'Reset và tạo dữ liệu mẫu với ID liên tục'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Xóa tất cả dữ liệu cũ
        self.stdout.write('Clearing old data...')
        ProductVariant.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Promotion.objects.all().delete()
        Color.objects.all().delete()
        Size.objects.all().delete()
        
        # Reset auto-increment (PostgreSQL)
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""
            SELECT setval(pg_get_serial_sequence('products_category', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('products_promotion', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('products_product', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('products_color', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('products_size', 'id'), 1, false);
        """)
        
        self.stdout.write('Creating new data...')
        
        # Tạo danh mục mới với ID 1, 2, 3, 4...
        categories_data = [
            ('Áo thun', 'Áo thun nam nữ đa dạng'),
            ('Quần jean', 'Quần jean chất lượng cao'),
            ('Váy', 'Váy thời trang'),
            ('Áo khoác', 'Áo khoác mùa đông'),
            ('Giày', 'Giày thể thao, sandal'),
            ('Túi xách', 'Túi xách thời trang'),
            ('Phụ kiện', 'Mũ, kính, thắt lưng'),
        ]
        
        created_cats = []
        for i, (name, desc) in enumerate(categories_data, start=1):
            cat = Category.objects.create(id=i, name=name, description=desc)
            created_cats.append(cat)
            self.stdout.write(f'  Created category {i}: {name}')
        
        # Tạo khuyến mãi
        promo = Promotion.objects.create(
            name='Giảm đầu mùa',
            discount_percent=15,
            start_date=today,
            end_date=today + timedelta(days=30),
        )
        self.stdout.write(f'  Created promotion: {promo.name}')
        
        # Tạo sản phẩm mới với ID 1, 2, 3...
        products_data = [
            ('Áo thun basic trắng', 'Áo thun cotton thoáng mát, form regular.', created_cats[0], Decimal('199000'), promo),
            ('Áo thun basic đen', 'Áo thun cotton đen dễ phối đồ.', created_cats[0], Decimal('199000'), None),
            ('Áo thun cổ tròn', 'Áo thun cổ tròn nhiều màu.', created_cats[0], Decimal('179000'), None),
            ('Áo thunoversize', 'Áo thun oversize phong cách Hàn Quốc.', created_cats[0], Decimal('220000'), None),
            ('Quần jean slim fit', 'Quần jean slim fit co giãn nhẹ.', created_cats[1], Decimal('399000'), promo),
            ('Quần jean baggy', 'Quần jean baggy unisex.', created_cats[1], Decimal('449000'), None),
            ('Quần jean boyfriend', 'Quần jean boyfriend nữ.', created_cats[1], Decimal('379000'), None),
            ('Quần jean skinny', 'Quần jean skinny ôm sát.', created_cats[1], Decimal('350000'), None),
            ('Váy midi hoa nhí', 'Váy midi dáng A, vải cotton.', created_cats[2], Decimal('299000'), None),
            ('Váy maxi', 'Váy maxi thanh lịch.', created_cats[2], Decimal('399000'), None),
            ('Áo khoác dù nam', 'Áo khoác chống nước nhẹ.', created_cats[3], Decimal('359000'), promo),
            ('Áo khoác len', 'Áo khoác len ấm áp.', created_cats[3], Decimal('459000'), None),
            ('Giày sneaker trắng', 'Giày sneaker trắng basic.', created_cats[4], Decimal('550000'), promo),
            ('Giày running', 'Giày chạy bộ thoáng khí.', created_cats[4], Decimal('750000'), None),
            ('Sandal da', 'Sandal da nam cao cấp.', created_cats[4], Decimal('420000'), None),
            ('Túi tote', 'Túi tote đi học, đi làm.', created_cats[5], Decimal('350000'), promo),
            ('Túi đeo chéo', 'Túi đeo chéo nam nữ.', created_cats[5], Decimal('280000'), None),
            ('Mũ bucket', 'Mũ bucket phong cách.', created_cats[6], Decimal('120000'), promo),
            ('Kính râm', 'Kính râm cao cấp.', created_cats[6], Decimal('250000'), None),
            ('Thắt lưng da', 'Thắt lưng da nam cao cấp.', created_cats[6], Decimal('180000'), None),
        ]
        
        created_products = []
        for i, (name, desc, category, price, promotion) in enumerate(products_data, start=1):
            product = Product.objects.create(
                id=i,
                name=name,
                description=desc,
                category=category,
                price=price,
                promotion=promotion,
            )
            created_products.append(product)
            self.stdout.write(f'  Created product {i}: {name}')
        
        # Tạo Color và Size
        colors = []
        for name, code in [('Đen', '#000000'), ('Trắng', '#FFFFFF'), ('Xanh', '#0000FF'), ('Đỏ', '#FF0000')]:
            color = Color.objects.create(name=name, code=code)
            colors.append(color)
        
        sizes = []
        for name in ['S', 'M', 'L', 'XL']:
            size = Size.objects.create(name=name)
            sizes.append(size)
        
        # Tạo ProductVariant
        for product in created_products:
            for color in colors[:2]:
                for size in sizes[:2]:
                    ProductVariant.objects.create(
                        product=product,
                        color=color,
                        size=size,
                        stock=10
                    )
        
        self.stdout.write(self.style.SUCCESS(f'\nCreated {len(created_cats)} categories (ID 1-{len(created_cats)})'))
        self.stdout.write(self.style.SUCCESS(f'Created {len(created_products)} products (ID 1-{len(created_products)})'))
        self.stdout.write(self.style.SUCCESS('\nNow use:'))
        self.stdout.write('  http://localhost:5173/products?category=1  (Áo thun)')
        self.stdout.write('  http://localhost:5173/products?category=2  (Quần jean)')
        self.stdout.write('  http://localhost:5173/products?category=3  (Váy)')
        self.stdout.write('  http://localhost:5173/products?category=4  (Áo khoác)')
        self.stdout.write('  http://localhost:5173/products?category=5  (Giày)')
        self.stdout.write('  http://localhost:5173/products?category=6  (Túi xách)')
        self.stdout.write('  http://localhost:5173/products?category=7  (Phụ kiện)')
