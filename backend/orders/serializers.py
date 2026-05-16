from django.contrib.auth.models import User
from rest_framework import serializers

from products.serializers import ProductSerializer, normalize_size_name
from .models import DiscountCode, Order, OrderItem, Shipping, ReturnRequest


class DiscountCodeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(read_only=True)
    effective_is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = DiscountCode
        fields = (
            "id",
            "name",
            "code",
            "discount_percent",
            "min_order_value",
            "start_date",
            "end_date",
            "is_active",
            "effective_is_active",
            "usage_limit",
            "used_count",
            "status",
            "status_label",
        )
        read_only_fields = ("used_count",)

    def validate_code(self, value: str) -> str:
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Vui lòng nhập mã giảm giá.")
        return code

    def validate_discount_percent(self, value: int) -> int:
        if value <= 0 or value > 100:
            raise serializers.ValidationError("Phần trăm giảm giá phải từ 1 đến 100.")
        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")
        return attrs


class OrderUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(source="product.product", read_only=True)
    variant_info = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "order", "product", "variant_info", "quantity", "price")
        read_only_fields = ("order",)

    def get_variant_info(self, obj: OrderItem):
        if not obj.product:
            return None
        return {
            "color": {"id": obj.product.color.id, "name": obj.product.color.name, "code": obj.product.color.code},
            "size": {"id": obj.product.size.id, "name": normalize_size_name(obj.product.size.name)},
        }


class ShippingNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipping
        fields = ("name", "phone", "address", "note")

class ReturnRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    order_total = serializers.CharField(source="order.total_price", read_only=True)
    order_items = serializers.SerializerMethodField()
 
    class Meta:
        model = ReturnRequest
        fields = [
            "id", "order", "user", "username", "reason", "description",
            "status", "admin_note", "order_total", "order_items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "username", "order_total", "order_items", "status", "admin_note", "created_at", "updated_at"]
 
    def get_order_items(self, obj):
        qs = OrderItem.objects.filter(order=obj.order).select_related(
            "product", "product__product", "product__product__category", "product__color", "product__size"
        )
        return OrderItemSerializer(qs, many=True, context=self.context).data
    
class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    user = OrderUserSerializer(read_only=True)
    shipping = serializers.SerializerMethodField()
    discount_code = serializers.CharField(source="discount_code_snapshot", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "subtotal",
            "discount_code",
            "discount_amount",
            "shipping_fee",
            "total_price",
            "payment_method",
            "gateway_status",
            "gateway_transaction_id",
            "inventory_deducted",
            "status",
            "confirmed_by_user",
            "completed_at",
            "created_at",
            "items",
            "shipping",
        )
        read_only_fields = (
            "user",
            "created_at",
            "items",
            "shipping",
            "discount_code",
            "confirmed_by_user",
            "completed_at",
            "payment_method",
            "gateway_status",
            "gateway_transaction_id",
            "inventory_deducted",
        )

    def validate_status(self, value: str) -> str:
        if not self.instance:
            return value
        current_status = self.instance.status
        if value == current_status:
            return value
        terminal_statuses = {"completed", "cancelled", "returning"}
        if current_status in terminal_statuses:
            raise serializers.ValidationError("Đơn hàng đã ở trạng thái hoàn thành và không thể thay đổi nữa.")
        return value

    def get_items(self, obj):
        qs = OrderItem.objects.filter(order=obj).select_related(
            "product", "product__product", "product__product__category", "product__color", "product__size"
        )
        return OrderItemSerializer(qs, many=True, context=self.context).data

    def get_shipping(self, obj):
        try:
            ship = obj.shipping
        except Shipping.DoesNotExist:
            return None
        return ShippingNestedSerializer(ship).data
