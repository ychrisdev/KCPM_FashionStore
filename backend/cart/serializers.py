from rest_framework import serializers

from products.models import Product, ProductVariant
from products.serializers import ProductSerializer, normalize_size_name
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(source="product.product", read_only=True)
    # Thông tin variant: màu sắc, size
    variant_info = serializers.SerializerMethodField()
    product_variant_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=ProductVariant.objects.select_related("product", "color", "size").all(),
        write_only=True,
        required=False,
    )
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        required=False,
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
    stock = serializers.IntegerField(source="product.stock", read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "cart",
            "product",
            "variant_info",
            "stock",
            "product_variant_id",
            "product_id",
            "quantity",
        )
        read_only_fields = ("cart",)

    def get_variant_info(self, obj: CartItem):
        """Lấy thông tin color và size của variant"""
        if not obj.product:
            return None
        return {
            "color": {"id": obj.product.color.id, "name": obj.product.color.name, "code": obj.product.color.code},
            "size": {"id": obj.product.size.id, "name": normalize_size_name(obj.product.size.name)},
        }

    def validate(self, attrs):
        # Cập nhật dòng giỏ (thường là PATCH số lượng)
        if self.instance is not None:
            if "quantity" in attrs:
                variant = self.instance.product
                variant.refresh_from_db(fields=["stock"])
                q = attrs["quantity"]
                if q > variant.stock:
                    raise serializers.ValidationError(
                        {
                            "quantity": (
                                f"Không đủ hàng. Còn {variant.stock} sản phẩm "
                                f"({variant.product.name}, {variant.color.name}/{normalize_size_name(variant.size.name)})."
                            )
                        }
                    )
            return attrs

        if attrs.get("product"):
            pass
        else:
            product_id = attrs.pop("product_id", None)
            if product_id:
                variant = ProductVariant.objects.filter(product=product_id).first()
                if variant:
                    attrs["product"] = variant
                else:
                    raise serializers.ValidationError(
                        {"product_id": "Sản phẩm này chưa có biến thể (variant)."}
                    )
            if not attrs.get("product"):
                raise serializers.ValidationError(
                    "Cần gửi product_variant_id hoặc product_id."
                )

        variant = attrs.get("product")
        qty = attrs.get("quantity", 1)
        if variant is not None:
            variant.refresh_from_db(fields=["stock"])
            cart = self.context.get("cart")
            if self.instance is None:
                existing = (
                    CartItem.objects.filter(cart=cart, product=variant).first()
                    if cart
                    else None
                )
                need = existing.quantity + qty if existing else qty
                if need > variant.stock:
                    label = f"{variant.product.name} ({variant.color.name}/{normalize_size_name(variant.size.name)})"
                    extra = (
                        f" Trong giỏ đã có {existing.quantity}."
                        if existing
                        else ""
                    )
                    raise serializers.ValidationError(
                        {
                            "quantity": (
                                f"Không đủ hàng cho {label}. Còn {variant.stock}, "
                                f"cần tổng {need}.{extra}"
                            )
                        }
                    )
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "user", "created_at", "items")
        read_only_fields = ("user", "created_at", "items")

    def get_items(self, obj):
        qs = CartItem.objects.filter(cart=obj).select_related(
            "product", "product__product", "product__product__category", "product__color", "product__size"
        )
        return CartItemSerializer(qs, many=True, context=self.context).data
