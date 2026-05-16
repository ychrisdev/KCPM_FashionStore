from django.conf import settings
from django.db import models
from rest_framework import serializers

from .models import Category, Promotion, Product, ProductImage, ProductVariant, Color, Size


def normalize_size_name(value: str) -> str:
    return value.strip().upper()


class CategorySerializer(serializers.ModelSerializer):
    """Đọc/ghi ảnh danh mục; response luôn là URL đầy đủ hoặc placeholder."""

    class Meta:
        model = Category
        fields = ("id", "name", "description", "image", "is_active")
        extra_kwargs = {"image": {"required": False, "allow_null": True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.image:
            url = instance.image.url
            data["image"] = request.build_absolute_uri(url) if request else url
        else:
            data["image"] = (
                f'https://via.placeholder.com/400x400?text={instance.name.replace(" ", "+")}'
            )
        return data


class PromotionSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = ("id", "name", "discount_percent", "start_date", "end_date", "is_active")

    def get_is_active(self, obj) -> bool:
        return obj.is_active

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.")
        return attrs


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "code")


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ("id", "name", "order")
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = normalize_size_name(data.get("name", ""))
        return data

    def validate_name(self, value: str) -> str:
        normalized = normalize_size_name(value)
        if not normalized:
            raise serializers.ValidationError("Vui long nhap size.")

        exists = Size.objects.filter(name__iexact=normalized).exclude(
            pk=self.instance.pk if self.instance else None
        )
        if exists.exists():
            raise serializers.ValidationError("Size nay da ton tai.")
        return normalized


class ProductVariantSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    color_id = serializers.PrimaryKeyRelatedField(
        source="color", queryset=Color.objects.all(), write_only=True
    )
    size = SizeSerializer(read_only=True)
    size_id = serializers.PrimaryKeyRelatedField(
        source="size", queryset=Size.objects.all(), write_only=True
    )
    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.all(), write_only=True
    )
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ("id", "product_id", "color", "color_id", "size", "size_id", "stock", "price", "effective_price",)

    def get_effective_price(self, obj) -> int:
        from decimal import Decimal, ROUND_HALF_UP
        base = Decimal(obj.get_price())
        promo = obj.product.promotion
        if promo and promo.is_active:
            base = base * (Decimal(100) - Decimal(promo.discount_percent)) / Decimal(100)
        return int(base.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def validate(self, attrs):
        product = attrs.get("product") or (
            self.instance.product if self.instance else None
        )
        color = attrs.get("color") or (
            self.instance.color if self.instance else None
        )
        size = attrs.get("size") or (self.instance.size if self.instance else None)
        if product and color and size:
            # Kiểm tra trùng lặp
            exists = ProductVariant.objects.filter(
                product=product, color=color, size=size
            ).exclude(pk=self.instance.pk if self.instance else None).exists()
            if exists:
                raise serializers.ValidationError(
                    "Biến thể này đã tồn tại (cùng sản phẩm, màu, size)."
                )
        return attrs

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image")

    def get_image(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True
    )
    promotion = PromotionSerializer(read_only=True)
    promotion_id = serializers.PrimaryKeyRelatedField(
        source="promotion",
        queryset=Promotion.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    # Ảnh đầu tiên của sản phẩm
    image = serializers.SerializerMethodField()
    # Tổng tồn kho (từ ProductVariant)
    stock = serializers.SerializerMethodField()
    # Giá gốc (trước khuyến mãi)
    old_price = serializers.SerializerMethodField()
    # Danh sách variants (màu sắc, kích thước, tồn kho)
    variants = serializers.SerializerMethodField()
    # Danh sách ảnh (cho admin)
    images = serializers.SerializerMethodField()
    # Cho phép upload ảnh khi tạo/sửa sản phẩm
    upload_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    clear_promotion = serializers.BooleanField(write_only=True, required=False)
    size_chart = serializers.SerializerMethodField()
    
    size_chart_upload = serializers.ImageField(
            write_only=True, required=False, allow_null=True
        )
    clear_size_chart = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "price",
            "old_price",
            "image",
            "images",
            "upload_images",
            "stock",
            "category",
            "category_id",
            "promotion",
            "promotion_id",
            "clear_promotion",
            "variants",
            "rating",
            "sold_count",
            "size_chart",
            "size_chart_upload",
            "clear_size_chart",
        )
        
    def get_size_chart(self, obj: Product) -> str | None:
        if not obj.size_chart:
            return None
        request = self.context.get("request")
        url = obj.size_chart.url
        return request.build_absolute_uri(url) if request else url

    def create(self, validated_data):
        upload_images = validated_data.pop('upload_images', [])
        validated_data.pop('clear_promotion', None)
        size_chart_upload = validated_data.pop('size_chart_upload', None)
        validated_data.pop('clear_size_chart', None)
        
        if size_chart_upload:
            validated_data['size_chart'] = size_chart_upload
        
        product = Product.objects.create(**validated_data)
        for image in upload_images:
            ProductImage.objects.create(product=product, image=image)
        return product

    def update(self, instance, validated_data):
        upload_images = validated_data.pop('upload_images', [])
        size_chart_upload = validated_data.pop('size_chart_upload', None)
        clear_size_chart = validated_data.pop('clear_size_chart', False)
        
        if validated_data.pop("clear_promotion", False):
            instance.promotion = None
            validated_data.pop("promotion", None)
        
        # Xử lý size_chart
        if size_chart_upload:
            instance.size_chart = size_chart_upload
        elif clear_size_chart:
            instance.size_chart = None
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        for image in upload_images:
            ProductImage.objects.create(product=instance, image=image)
        return instance

    def get_image(self, obj: Product) -> str:
        """Lấy URL ảnh đầu tiên của sản phẩm, hoặc trả về placeholder"""
        first_img = ProductImage.objects.filter(product=obj).first()
        if first_img and first_img.image:
            img_url = first_img.image.url
            # Nếu có request context, dùng build_absolute_uri
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(img_url)
            # Nếu không, nối với MEDIA_URL
            if img_url and not img_url.startswith('http'):
                return settings.MEDIA_URL + img_url.lstrip('/')
            return img_url
        # Trả về placeholder nếu không có ảnh
        return f'https://via.placeholder.com/400x500?text={obj.name.replace(" ", "+")}'
    
    def get_images(self, obj):
        images = ProductImage.objects.filter(product=obj)
        return ProductImageSerializer(images, many=True, context=self.context).data

    def get_stock(self, obj: Product) -> int:
        """Tính tổng tồn kho từ các variant"""
        total = ProductVariant.objects.filter(product=obj).aggregate(total=models.Sum("stock"))
        return total["total"] or 0

    def get_old_price(self, obj: Product) -> float | None:
        if obj.promotion and obj.promotion.is_active:
            discount = obj.promotion.discount_percent
            original_price = float(obj.price) / (1 - discount / 100)
            return round(original_price)
        return None

    def get_variants(self, obj: Product) -> list:
        variants = ProductVariant.objects.filter(product=obj).select_related("color", "size").order_by("size__order", "size__name")
        promo = obj.promotion if (obj.promotion and obj.promotion.is_active) else None
        result = []
        for v in variants:
            base_price = v.get_price()
            effective = base_price
            if promo:
                from decimal import Decimal, ROUND_HALF_UP
                effective = int(
                    (Decimal(base_price) * (Decimal(100) - Decimal(promo.discount_percent)) / Decimal(100))
                    .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                )
            result.append({
                "id": v.id,
                "color": {"id": v.color.id, "name": v.color.name, "code": v.color.code},
                "size": {"id": v.size.id, "name": normalize_size_name(v.size.name),
                "order": v.size.order},
                "stock": v.stock,
                "price": base_price,
                "effective_price": effective,
            })
        return result
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        promo = data.get("promotion")
        if promo and not promo.get("is_active", False):
            data["promotion"] = None
        return data
    
    def validate_promotion_id(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError(
                "Khuyến mãi này đã hết hạn hoặc chưa bắt đầu, không thể gán cho sản phẩm."
            )
        return value
