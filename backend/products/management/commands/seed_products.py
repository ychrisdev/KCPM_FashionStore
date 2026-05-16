"""
Lệnh tạo dữ liệu mẫu: danh mục, khuyến mãi và sản phẩm.
Chạy: python manage.py seed_products
"""
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import Category, Promotion, Product, ProductImage, Color, Size, ProductVariant


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu: danh mục, khuyến mãi và sản phẩm'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write('Creating sample data...')

        # Danh mục
        categories_data = [
            ('Áo thun', 'Áo thun nam nữ đa dạng'),
            ('Quần jean', 'Quần jean chất lượng cao'),
            ('Váy', 'Váy thời trang'),
            ('Áo khoác', 'Áo khoác mùa đông'),
        ]
        created_cats = []
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            created_cats.append(cat)
        self.stdout.write(self.style.SUCCESS(f'Categories: {len(created_cats)}'))

        # Khuyến mãi
        promo, _ = Promotion.objects.get_or_create(
            name='Giảm đầu mùa',
            defaults={
                'discount_percent': 15,
                'start_date': today,
                'end_date': today + timedelta(days=30),
            }
        )
        self.stdout.write(self.style.SUCCESS('Promotion ready'))

        # Sản phẩm (đủ để có id 1, 2, 3, 4, 5, 6...)
        products_data = [
            ('Áo thun basic trắng', 'Áo thun cotton thoáng mát, form regular.', created_cats[0], Decimal('199000'), promo),
            ('Áo thun basic đen', 'Áo thun cotton đen dễ phối đồ.', created_cats[0], Decimal('199000'), None),
            ('Quần jean slim fit', 'Quần jean slim fit co giãn nhẹ.', created_cats[1], Decimal('399000'), promo),
            ('Quần jean baggy', 'Quần jean baggy unisex.', created_cats[1], Decimal('449000'), None),
            ('Váy midi hoa nhí', 'Váy midi dáng A, vải cotton.', created_cats[2], Decimal('299000'), None),
            ('Áo khoác dù nam', 'Áo khoác chống nước nhẹ.', created_cats[3], Decimal('359000'), promo),
            ('Áo thun cổ tròn', 'Áo thun cổ tròn nhiều màu.', created_cats[0], Decimal('179000'), None),
            ('Quần jean boyfriend', 'Quần jean boyfriend nữ.', created_cats[1], Decimal('379000'), None),
        ]
        created = 0
        created_products = []
        for name, desc, category, price, promotion in products_data:
            product, created_this = Product.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'category': category,
                    'price': price,
                    'promotion': promotion,
                }
            )
            created_products.append(product)
            if created_this:
                created += 1

        # Tạo Color và Size mẫu
        colors = []
        for name, code in [('Đen', '#000000'), ('Trắng', '#FFFFFF'), ('Xanh', '#0000FF'), ('Đỏ', '#FF0000')]:
            color, _ = Color.objects.get_or_create(name=name, defaults={'code': code})
            colors.append(color)

        sizes = []
        for name in ['S', 'M', 'L', 'XL']:
            size, _ = Size.objects.get_or_create(name=name)
            sizes.append(size)

        # Tạo ProductVariant cho mỗi sản phẩm (không tạo ProductImage vì cần upload file thực)
        for product in created_products:
            for color in colors[:2]:  # Mỗi sản phẩm có 2 màu
                for size in sizes[:2]:  # Mỗi sản phẩm có 2 size
                    ProductVariant.objects.get_or_create(
                        product=product,
                        color=color,
                        size=size,
                        defaults={'stock': 10}
                    )

        self.stdout.write(self.style.SUCCESS(f'Created {created} new products (ids 1-{len(products_data)} available).'))
        self.stdout.write(self.style.SUCCESS(f'Sample images and variants added for products.'))
        self.stdout.write('Visit http://localhost:5173/product/6 to see product detail.')
