from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.serializers import UserSerializer
from core.permissions import is_staff
from products.serializers import normalize_size_name
from .models import Review, Comment


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product_name = serializers.SerializerMethodField()
    variant_info = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "user",
            "product",
            "product_name",
            "variant_info",
            "rating",
            "feedback_type",
            "content",
            "is_visible",
            "created_at",
        )
        read_only_fields = ("user", "created_at")

    def validate(self, attrs):
        request = self.context.get("request")
        if request and not is_staff(request.user):
            attrs.pop("is_visible", None)

            from orders.models import OrderItem
            variant = attrs.get("product")
            if variant:
                has_purchased = OrderItem.objects.filter(
                    order__user=request.user,
                    order__status="completed",
                    product=variant,
                ).exists()
                if not has_purchased:
                    raise serializers.ValidationError(
                        {"product": "Bạn chỉ có thể đánh giá sản phẩm đã mua và nhận hàng thành công."}
                    )

            if variant:
                already_reviewed = Review.objects.filter(
                    user=request.user, product=variant
                ).exists()
                if already_reviewed:
                    raise serializers.ValidationError(
                        {"product": "Bạn đã đánh giá sản phẩm này rồi."}
                    )

        return attrs

    def get_product_name(self, obj):
        return obj.product.product.name if obj.product else ''

    def get_variant_info(self, obj):
        if obj.product:
            return {
                'color': {'id': obj.product.color.id, 'name': obj.product.color.name, 'code': obj.product.color.code},
                'size': {'id': obj.product.size.id, 'name': normalize_size_name(obj.product.size.name)}
            }
        return None


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "user", "product", "content", "created_at")
        read_only_fields = ("user", "created_at")
