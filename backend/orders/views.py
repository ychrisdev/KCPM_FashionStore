from django.db import models
from decimal import Decimal

from django.utils import timezone
from datetime import timedelta
from .constants import RETURN_WINDOW

from django.db import transaction
from django.db.models import F
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from cart.models import Cart, CartItem
from core.permissions import is_staff, IsAdminOrStaff, IsOrderStaff
from products.models import ProductVariant
from wallets.services import credit_order_refund_to_user_wallet, debit_wallet_for_order_payment
from products.serializers import normalize_size_name
from .mail import (
    send_order_confirmation_email,
    send_order_shipped_email,
    send_return_refund_completed_email,
)
from .models import DiscountCode, Order, OrderItem, Shipping, ReturnRequest
from .pricing import build_order_totals, normalize_discount_code, unit_price_vnd
from .serializers import DiscountCodeSerializer, OrderItemSerializer, OrderSerializer, ReturnRequestSerializer


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class DiscountCodeViewSet(viewsets.ModelViewSet):
    queryset = DiscountCode.objects.all().order_by("-id")
    serializer_class = DiscountCodeSerializer
    permission_classes = [IsAdminOrStaff]

    @action(detail=False, methods=["get"], url_path="active", permission_classes=[AllowAny])
    def active(self, request):
        today = timezone.localdate()
        codes = DiscountCode.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
        ).filter(
            models.Q(usage_limit__isnull=True) | models.Q(used_count__lt=models.F("usage_limit"))
        ).order_by("-id")
        serializer = self.get_serializer(codes, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderPagination

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def approve_refund(self, request, pk=None):
        order_pk = self.get_object().pk
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order_pk)
                if order.status == "refunded":
                    return Response(
                        {"detail": "Đơn đã được hoàn tiền trước đó."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                credit_order_refund_to_user_wallet(
                    order.user,
                    order_id=order.id,
                    total_price=order.total_price,
                    reason_label="Hoàn tiền đơn hàng (duyệt hoàn)",
                )
                order.status = "refunded"
                order.save(update_fields=["status"])
            return Response({"detail": "Đã hoàn tiền thành công vào ví!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=["post"], url_path="confirm-received")
    def confirm_received(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user:
            return Response(
                {"detail": "Bạn không có quyền thực hiện thao tác này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status != "awaiting_confirmation":
            return Response(
                {"detail": "Chỉ có thể xác nhận nhận hàng khi đơn đang chờ xác nhận."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = "completed"
        order.confirmed_by_user = True
        order.completed_at = timezone.now()
        order.save(update_fields=["status", "confirmed_by_user", "completed_at"])
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user:
            return Response(
                {"detail": "Bạn không có quyền hủy đơn hàng này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status != "pending":
            return Response(
                {"detail": "Chỉ có thể hủy đơn hàng đang chờ xử lý."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            items = OrderItem.objects.filter(order=order).select_related("product")
            for item in items:
                ProductVariant.objects.filter(pk=item.product_id).update(
                    stock=F("stock") + item.quantity
                )
            if order.gateway_status == "paid":
                credit_order_refund_to_user_wallet(
                    order.user,
                    order_id=order.id,
                    total_price=order.total_price,
                    reason_label="Hoàn tiền hủy đơn hàng",
                )
            order.status = "cancelled"
            order.save(update_fields=["status"])
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="retry-payment")
    def retry_payment(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user:
            return Response(
                {"detail": "Bạn không có quyền thực hiện thao tác này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status != "pending":
            return Response(
                {"detail": "Chỉ có thể thanh toán lại cho đơn hàng đang chờ xử lý."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.gateway_status == "paid":
            return Response(
                {"detail": "Đơn hàng này đã được thanh toán."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_payment = (request.data.get("payment_method") or order.payment_method).strip().lower()
        if raw_payment not in {"vnpay", "momo", "zalopay", "cod", "wallet"}:
            return Response(
                {"detail": "Phương thức thanh toán không được hỗ trợ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if raw_payment == "wallet":
            try:
                with transaction.atomic():
                    order_locked = Order.objects.select_for_update().get(pk=order.pk)
                    if order_locked.user_id != request.user.id:
                        return Response(
                            {"detail": "Bạn không có quyền thực hiện thao tác này."},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    if order_locked.status != "pending":
                        return Response(
                            {"detail": "Chỉ có thể thanh toán lại cho đơn hàng đang chờ xử lý."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if order_locked.gateway_status == "paid":
                        return Response(
                            {"detail": "Đơn hàng này đã được thanh toán."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    debit_wallet_for_order_payment(
                        request.user,
                        order_id=order_locked.id,
                        amount=order_locked.total_price,
                    )
                    order_locked.payment_method = "wallet"
                    order_locked.gateway_status = "paid"
                    order_locked.gateway_transaction_id = ""
                    order_locked.save(
                        update_fields=["payment_method", "gateway_status", "gateway_transaction_id"]
                    )
                    oid = order_locked.id
                transaction.on_commit(lambda o=oid: send_order_confirmation_email(o))
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            order.refresh_from_db()
            return Response(self.get_serializer(order).data, status=status.HTTP_200_OK)

        if raw_payment != order.payment_method:
            order.payment_method = raw_payment
            order.save(update_fields=["payment_method"])

        payload = {"status": "ok", "payment_method": raw_payment}
        if raw_payment == "vnpay":
            from payments import vnpay as vnpay_mod
            try:
                payload["payment_url"] = vnpay_mod.build_payment_url(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                )
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        elif raw_payment == "momo":
            from payments import momo as momo_mod
            try:
                payload["payment_url"] = momo_mod.create_payment(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                )
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        elif raw_payment == "zalopay":
            from payments import zalopay as zalopay_mod
            try:
                pay_url, app_tid = zalopay_mod.create_payment(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                    str(request.user.pk),
                )
                Order.objects.filter(pk=order.pk).update(zalopay_app_trans_id=app_tid)
                payload["payment_url"] = pay_url
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="zalopay-sync")
    def zalopay_sync(self, request, pk=None):
        """Đối soát trạng thái với ZaloPay /v2/query (bù khi IPN callback không tới server)."""
        from payments import zalopay as zalopay_mod
        from payments.services import mark_order_paid

        order = self.get_object()
        if order.user != request.user:
            return Response(
                {"detail": "Bạn không có quyền thực hiện thao tác này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.payment_method != "zalopay":
            return Response(
                {"detail": "Đơn hàng không dùng ZaloPay."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.gateway_status == "paid":
            return Response(self.get_serializer(order).data)

        atid = (order.zalopay_app_trans_id or "").strip()
        if not atid:
            return Response(
                {
                    "detail": "Chưa có mã giao dịch ZaloPay để đối soát. Hãy dùng \"Thanh toán lại\" để tạo phiên thanh toán mới.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            body = zalopay_mod.query_order_status(atid)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        paid, zp = zalopay_mod.is_query_result_paid(order.total_price, body)
        if paid:
            mark_order_paid(order.pk, zp)
            order.refresh_from_db()
            return Response(self.get_serializer(order).data)

        msg = (
            body.get("return_message")
            or body.get("sub_return_message")
            or "ZaloPay chưa xác nhận thanh toán cho giao dịch này."
        )
        data = dict(self.get_serializer(order).data)
        data["zalopay_pending_message"] = msg
        return Response(data, status=status.HTTP_200_OK)

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsOrderStaff()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        import datetime
        cutoff = timezone.now() - datetime.timedelta(days=2)
        Order.objects.filter(
            status="awaiting_confirmation",
            updated_at__lte=cutoff,
        ).update(status="completed")
        if is_staff(user):
            qs = Order.objects.select_related("user", "discount_code").prefetch_related("shipping").all()
        else:
            qs = Order.objects.select_related("user", "discount_code").filter(user=user)

        qs = qs.order_by("-created_at")

        if self.action == "list" and is_staff(user):
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
            date_from = self.request.query_params.get("date_from")
            date_to = self.request.query_params.get("date_to")
            if date_from:
                qs = qs.filter(created_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        order = serializer.save()
        if old_status != order.status and order.status == "shipping":
            oid = order.pk
            transaction.on_commit(lambda o=oid: send_order_shipped_email(o))

    def _validation_error_message(self, exc: ValidationError) -> str:
        detail = exc.detail
        if isinstance(detail, list):
            return str(detail[0]) if detail else "Du lieu khong hop le."
        if isinstance(detail, dict):
            first_value = next(iter(detail.values()), "Du lieu khong hop le.")
            if isinstance(first_value, list):
                return str(first_value[0]) if first_value else "Du lieu khong hop le."
            return str(first_value)
        return str(detail)

    def _normalize_cart_item_ids(self, raw_ids):
        if raw_ids in (None, ""):
            return None
        if not isinstance(raw_ids, list):
            raise ValidationError("Danh sach san pham thanh toan khong hop le.")

        normalized_ids = []
        for raw_id in raw_ids:
            try:
                normalized_id = int(raw_id)
            except (TypeError, ValueError):
                raise ValidationError("Danh sach san pham thanh toan khong hop le.")
            if normalized_id <= 0:
                raise ValidationError("Danh sach san pham thanh toan khong hop le.")
            normalized_ids.append(normalized_id)

        if not normalized_ids:
            raise ValidationError("Vui long chon san pham de thanh toan.")
        return list(dict.fromkeys(normalized_ids))

    def _load_cart_items(self, user, *, lock: bool = False, cart_item_ids=None):
        # Trùng với CartViewSet: giỏ mới nhất — tránh .first() không order_by (lệch giỏ so với API /cart/carts/).
        cart_qs = Cart.objects.filter(user=user).order_by("-created_at")
        if lock:
            cart_qs = cart_qs.select_for_update()
        cart = cart_qs.first()
        if not cart:
            raise ValidationError("Giỏ hàng trống.")

        cart_items_qs = CartItem.objects.filter(cart=cart).select_related(
            "product",
            "product__product",
            "product__color",
            "product__size",
        ).order_by("product_id")
        if cart_item_ids is not None:
            cart_items_qs = cart_items_qs.filter(id__in=cart_item_ids)
        if lock:
            cart_items_qs = cart_items_qs.select_for_update()

        cart_items = list(cart_items_qs)
        if not cart_items and cart_item_ids is None:
            raise ValidationError("Giỏ hàng trống.")
        if cart_item_ids is not None and len(cart_items) != len(cart_item_ids):
            raise ValidationError("Mot so san pham da chon khong con trong gio hang.")
        if not cart_items and cart_item_ids is not None:
            raise ValidationError("Vui long chon san pham de thanh toan.")
        return cart, cart_items

    def _build_pricing_payload(self, cart_items, discount_code=None):
        subtotal = Decimal("0")
        for cart_item in cart_items:
            subtotal += unit_price_vnd(cart_item.product) * cart_item.quantity
        
        shipping_fee, discount_amount, total = build_order_totals(subtotal, discount_code)
        return {
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "discount_amount": discount_amount,
            "total_price": total,
            "discount_code": discount_code.code if discount_code else "",
            "discount_name": discount_code.name if discount_code else "",
            "discount_percent": discount_code.discount_percent if discount_code else 0,
        }

    @action(detail=False, methods=["post"], url_path="discount-preview")
    def discount_preview(self, request):
        user = request.user
        code = normalize_discount_code(request.data.get("discount_code"))
        try:
            cart_item_ids = self._normalize_cart_item_ids(request.data.get("cart_item_ids"))
        except ValidationError as exc:
            return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _cart, cart_items = self._load_cart_items(user, lock=False, cart_item_ids=cart_item_ids)
        except ValidationError as exc:
            return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        discount_code = None
        if code:
            discount_code = DiscountCode.objects.filter(code__iexact=code).first()
            if discount_code is None:
                return Response({"detail": "Mã giảm giá không tồn tại."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pricing = self._build_pricing_payload(cart_items, discount_code)
        except ValidationError as exc:
            return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serialized = {
            "subtotal": str(pricing["subtotal"]),
            "shipping_fee": str(pricing["shipping_fee"]),
            "discount_amount": str(pricing["discount_amount"]),
            "total_price": str(pricing["total_price"]),
            "discount_code": pricing["discount_code"],
            "discount_name": pricing["discount_name"],
            "discount_percent": pricing["discount_percent"],
        }
        return Response(serialized)

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        user = request.user
        name = request.data.get("name", "").strip()
        phone = request.data.get("phone", "").strip()
        address = request.data.get("address", "").strip()
        note = (request.data.get("note") or "").strip()
        discount_code_value = normalize_discount_code(request.data.get("discount_code"))
        try:
            cart_item_ids = self._normalize_cart_item_ids(request.data.get("cart_item_ids"))
        except ValidationError as exc:
            return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if len(note) > 2000:
            note = note[:2000]

        if not name or not phone or not address:
            return Response(
                {"detail": "Vui lòng điền đầy đủ họ tên, số điện thoại và địa chỉ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_payment = {c[0] for c in Order.PAYMENT_METHOD_CHOICES}
        raw_payment = (request.data.get("payment_method") or "cod").strip().lower()
        payment_method = raw_payment if raw_payment in allowed_payment else "cod"
        if payment_method in ("vnpay", "momo", "zalopay"):
            gateway_status = "pending"
        elif payment_method == "wallet":
            gateway_status = "paid"
        else:
            gateway_status = "none"

        with transaction.atomic():
            try:
                cart, cart_items = self._load_cart_items(user, lock=True, cart_item_ids=cart_item_ids)
            except ValidationError as exc:
                return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

            variant_ids = sorted({cart_item.product_id for cart_item in cart_items})
            locked_variants = list(
                ProductVariant.objects.select_for_update()
                .filter(id__in=variant_ids)
                .select_related("product", "color", "size")
                .order_by("id")
            )
            variants_map = {variant.id: variant for variant in locked_variants}
            if len(variants_map) != len(variant_ids):
                return Response(
                    {"detail": "Có sản phẩm trong giỏ không còn tồn tại."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            line_build = []
            subtotal = Decimal("0")
            for cart_item in cart_items:
                variant = variants_map[cart_item.product_id]
                if variant.stock < cart_item.quantity:
                    label = f"{variant.product.name} ({variant.color.name}/{normalize_size_name(variant.size.name)})"
                    return Response(
                        {"detail": f"Không đủ hàng: {label}. Còn {variant.stock}, cần {cart_item.quantity}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                unit = unit_price_vnd(variant)
                subtotal += unit * cart_item.quantity
                line_build.append((cart_item, variant, unit))

            discount_code = None
            if discount_code_value:
                discount_code = DiscountCode.objects.select_for_update().filter(code__iexact=discount_code_value).first()
                if discount_code is None:
                    return Response(
                        {"detail": "Mã giảm giá không tồn tại."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            try:
                shipping_fee, discount_amount, total_price = build_order_totals(subtotal, discount_code)
            except ValidationError as exc:
                return Response({"detail": self._validation_error_message(exc)}, status=status.HTTP_400_BAD_REQUEST)

            for cart_item, variant, _unit in line_build:
                rows = ProductVariant.objects.filter(pk=variant.pk, stock__gte=cart_item.quantity).update(
                    stock=F("stock") - cart_item.quantity
                )
                if rows != 1:
                    raise ValidationError(
                        "Không thể cập nhật tồn kho. Có thể sản phẩm đã hết hàng trong lúc đặt. Vui lòng thử lại."
                    )

            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                discount_code=discount_code,
                discount_code_snapshot=discount_code.code if discount_code else "",
                discount_amount=discount_amount,
                shipping_fee=shipping_fee,
                total_price=total_price,
                payment_method=payment_method,
                gateway_status=gateway_status,
                inventory_deducted=True,
            )
            for cart_item, variant, unit in line_build:
                OrderItem.objects.create(
                    order=order,
                    product=variant,
                    quantity=cart_item.quantity,
                    price=unit,
                )
                
            from products.models import Product as ProductModel
            product_qty_map: dict[int, int] = {}
            for cart_item, variant, _unit in line_build:
                pid = variant.product_id
                product_qty_map[pid] = product_qty_map.get(pid, 0) + cart_item.quantity
            for pid, qty in product_qty_map.items():
                ProductModel.objects.filter(pk=pid).update(sold_count=F("sold_count") + qty)

            if discount_code is not None:
                DiscountCode.objects.filter(pk=discount_code.pk).update(used_count=F("used_count") + 1)

            Shipping.objects.create(order=order, name=name, phone=phone, address=address, note=note)
            CartItem.objects.filter(cart=cart, id__in=[cart_item.id for cart_item, _variant, _unit in line_build]).delete()

            if payment_method == "wallet":
                try:
                    debit_wallet_for_order_payment(
                        user,
                        order_id=order.id,
                        amount=total_price,
                    )
                except ValueError as exc:
                    raise ValidationError(str(exc))

            order_id_for_email = order.id
            if payment_method == "cod":
                transaction.on_commit(lambda oid=order_id_for_email: send_order_confirmation_email(oid))
            elif payment_method == "wallet":
                transaction.on_commit(lambda oid=order_id_for_email: send_order_confirmation_email(oid))

        serializer = OrderSerializer(order)
        payload = dict(serializer.data)
        if payment_method == "vnpay":
            from payments import vnpay as vnpay_mod

            try:
                payload["payment_url"] = vnpay_mod.build_payment_url(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                )
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        elif payment_method == "momo":
            from payments import momo as momo_mod

            try:
                payload["payment_url"] = momo_mod.create_payment(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                )
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        elif payment_method == "zalopay":
            from payments import zalopay as zalopay_mod

            try:
                pay_url, app_tid = zalopay_mod.create_payment(
                    request,
                    order.id,
                    order.total_price,
                    f"Thanh toan don hang #{order.id}",
                    str(user.pk),
                )
                Order.objects.filter(pk=order.pk).update(zalopay_app_trans_id=app_tid)
                payload["payment_url"] = pay_url
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_201_CREATED)

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOrderStaff()]

    def get_queryset(self):
        user = self.request.user
        if is_staff(user):
            return OrderItem.objects.all().select_related(
                "order", "product", "product__product", "product__product__category", "product__color", "product__size"
            )
        return OrderItem.objects.filter(order__user=user).select_related(
            "order", "product", "product__product", "product__product__category", "product__color", "product__size"
        )


class ReturnRequestViewSet(viewsets.ModelViewSet):
    queryset = ReturnRequest.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = ReturnRequest.objects.select_related("order", "user").prefetch_related(
            "order__orderitem_set__product__product__category",
            "order__orderitem_set__product__color",
            "order__orderitem_set__product__size",
        )
        if is_staff(user):
            qs = base_qs.all()
            status_filter = self.request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)
            return qs
        return base_qs.filter(user=user)

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsOrderStaff()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        order_id = request.data.get("order")

        if not order_id:
            return Response({"detail": "Thiếu order id."}, status=400)

        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return Response({"detail": "Order id không hợp lệ."}, status=400)

        try:
            order = Order.objects.get(pk=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Đơn hàng không tồn tại."}, status=400)

        if order.status not in ("shipping", "awaiting_confirmation", "completed"):
            return Response(
                {"detail": "Chỉ có thể yêu cầu trả hàng cho đơn đang giao hoặc đã hoàn thành."},
                status=400,
            )
        
        if order.status == "completed" and order.confirmed_by_user:
            if timezone.now() > order.completed_at + RETURN_WINDOW:
                return Response({"detail": "Đã quá thời hạn hoàn trả, không thể gửi yêu cầu."}, status=400)

        if ReturnRequest.objects.filter(order=order, user=request.user).exists():
            return Response(
                {"detail": "Bạn đã gửi yêu cầu trả hàng cho đơn này rồi."},
                status=400,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, order=order)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        if not is_staff(request.user):
            return Response({"detail": "Không có quyền."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.status != "pending":
            return Response({"detail": "Chỉ duyệt được yêu cầu đang chờ."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            obj.status = "approved"
            obj.admin_note = request.data.get("admin_note", "")
            obj.save(update_fields=["status", "admin_note", "updated_at"])
            Order.objects.filter(
                pk=obj.order_id,
                status__in=["shipping", "awaiting_confirmation"]
            ).update(status="returning")
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        if not is_staff(request.user):
            return Response({"detail": "Không có quyền."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.status != "pending":
            return Response({"detail": "Chỉ từ chối được yêu cầu đang chờ."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            obj.status = "rejected"
            obj.admin_note = request.data.get("admin_note", "")
            obj.save(update_fields=["status", "admin_note", "updated_at"])
            Order.objects.filter(
                pk=obj.order_id,
                status__in=["shipping", "awaiting_confirmation"]
            ).update(status="completed")
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        if not is_staff(request.user):
            return Response({"detail": "Không có quyền."}, status=status.HTTP_403_FORBIDDEN)
        rr_pk = int(self.kwargs["pk"])
        try:
            with transaction.atomic():
                obj = (
                    ReturnRequest.objects.select_for_update()
                    .select_related("order")
                    .get(pk=rr_pk)
                )
                if obj.status != "approved":
                    return Response(
                        {"detail": "Chỉ hoàn thành được yêu cầu đã duyệt."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                order = Order.objects.select_for_update().get(pk=obj.order_id)
                if order.status == "refunded":
                    return Response(
                        {"detail": "Đơn đã được hoàn tiền, không thể hoàn tất lại."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # Hoàn tiền vào ví của tài khoản đã gửi yêu cầu trả hàng
                credit_order_refund_to_user_wallet(
                    obj.user,
                    order_id=order.id,
                    total_price=order.total_price,
                    reason_label="Hoàn tiền trả hàng",
                )
                obj.status = "completed"
                obj.admin_note = request.data.get("admin_note", obj.admin_note)
                obj.save(update_fields=["status", "admin_note", "updated_at"])
                order.status = "refunded"
                order.save(update_fields=["status"])
                rid = obj.pk
                transaction.on_commit(lambda r=rid: send_return_refund_completed_email(r))
        except ReturnRequest.DoesNotExist:
            return Response({"detail": "Không tìm thấy yêu cầu."}, status=status.HTTP_404_NOT_FOUND)

        obj = ReturnRequest.objects.select_related("order", "user").get(pk=rr_pk)
        return Response(self.get_serializer(obj).data)