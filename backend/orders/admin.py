from django.contrib import admin

from .models import DiscountCode, Order, OrderItem, ReturnRequest, Shipping


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "discount_percent",
        "min_order_value",
        "is_active",
        "start_date",
        "end_date",
        "used_count",
        "usage_limit",
    )
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("code", "name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "subtotal",
        "discount_amount",
        "shipping_fee",
        "total_price",
        "payment_method",
        "gateway_status",
        "inventory_deducted",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "gateway_status", "created_at")
    search_fields = ("user__username", "discount_code_snapshot")
    # confirmed_by_user và completed_at do API tự set, không cho sửa tay
    readonly_fields = ("confirmed_by_user", "completed_at", "created_at", "gateway_transaction_id")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price")


@admin.register(Shipping)
class ShippingAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "phone")
    search_fields = ("name", "phone")


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "reason", "status", "created_at", "updated_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("user__username", "order__id")
    readonly_fields = ("order", "user", "reason", "description", "created_at", "updated_at")