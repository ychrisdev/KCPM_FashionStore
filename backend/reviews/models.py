from django.db import models
from django.contrib.auth.models import User

from products.models import ProductVariant


class Review(models.Model):
    FEEDBACK_TYPES = [
        ('quality', 'Chất lượng sản phẩm'),
        ('price', 'Giá cả'),
        ('shipping', 'Vấn đề giao hàng'),
        ('size', 'Kích thước/Size'),
        ('service', 'Chăm sóc khách hàng'),
        ('other', 'Khác'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES, default='quality')
    content = models.TextField(blank=True, default='')
    is_visible = models.BooleanField(default=True, help_text='Hiển thị trên trang sản phẩm')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
