import random
import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Avg, Sum, F
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Product, ProductVariant, Promotion
from orders.models import Order, OrderItem, Shipping, DiscountCode, ReturnRequest
from reviews.models import Review

User = get_user_model()

COMMENTS = [
    "Sản phẩm rất tốt!",
    "Đáng tiền",
    "Chất lượng ổn",
    "Giao hàng nhanh",
    "Không như mong đợi",
    "Mình rất hài lòng",
    "Sẽ mua lại lần sau",
]

EXTRA_STATUSES = ["pending", "shipping", "awaiting_confirmation", "returning", "cancelled", "refunded"]
EXTRA_ORDERS_PER_STATUS = 150
DISCOUNTED_ORDERS_COUNT = 500
RETURN_REQUESTS_COUNT = 10

DATE_START = datetime.datetime(2026, 4, 10, 0, 0, 0, tzinfo=datetime.timezone.utc)
DATE_END   = datetime.datetime(2026, 4, 23, 23, 59, 59, tzinfo=datetime.timezone.utc)
DATE_RANGE_SECONDS = int((DATE_END - DATE_START).total_seconds())

# Dữ liệu seed cho Promotion
PROMOTION_DATA = [
    {"name": "Flash Sale Tháng 4",     "discount_percent": 10, "start_date": datetime.date(2026, 4,  1), "end_date": datetime.date(2026, 4, 30)},
    {"name": "Mừng Lễ 30/4",           "discount_percent": 15, "start_date": datetime.date(2026, 4, 20), "end_date": datetime.date(2026, 5,  2)},
    {"name": "Summer Sale",             "discount_percent": 20, "start_date": datetime.date(2026, 5,  1), "end_date": datetime.date(2026, 5, 31)},
    {"name": "Khai Trương Online",      "discount_percent": 25, "start_date": datetime.date(2026, 3,  1), "end_date": datetime.date(2026, 3, 31)},
    {"name": "Clearance Sale",          "discount_percent": 30, "start_date": datetime.date(2026, 4, 15), "end_date": datetime.date(2026, 4, 25)},
    {"name": "Ngày Phụ Nữ 8/3",        "discount_percent": 12, "start_date": datetime.date(2026, 3,  6), "end_date": datetime.date(2026, 3, 10)},
    {"name": "Back to School",          "discount_percent": 18, "start_date": datetime.date(2026, 8, 20), "end_date": datetime.date(2026, 9,  5)},
    {"name": "Siêu Sale Cuối Tuần",     "discount_percent":  8, "start_date": datetime.date(2026, 4, 18), "end_date": datetime.date(2026, 4, 19)},
    {"name": "Tri Ân Khách Hàng",       "discount_percent": 22, "start_date": datetime.date(2026, 6,  1), "end_date": datetime.date(2026, 6, 15)},
    {"name": "Độc Thân 11/11",          "discount_percent": 50, "start_date": datetime.date(2026,11, 11), "end_date": datetime.date(2026,11, 11)},
]

# Dữ liệu seed cho DiscountCode
DISCOUNT_CODE_DATA = [
    {"name": "Giảm 5% cho đơn 200k",   "code": "SALE5",    "discount_percent":  5, "min_order_value": 200000,  "start_date": datetime.date(2026, 4,  1), "end_date": datetime.date(2026, 4, 30), "usage_limit": 100},
    {"name": "Giảm 10% cho đơn 300k",  "code": "SAVE10",   "discount_percent": 10, "min_order_value": 300000,  "start_date": datetime.date(2026, 4,  1), "end_date": datetime.date(2026, 4, 30), "usage_limit": 80},
    {"name": "Giảm 15% VIP",           "code": "VIP15",    "discount_percent": 15, "min_order_value": 500000,  "start_date": datetime.date(2026, 4, 10), "end_date": datetime.date(2026, 4, 30), "usage_limit": 50},
    {"name": "Giảm 20% Flash",         "code": "FLASH20",  "discount_percent": 20, "min_order_value": 400000,  "start_date": datetime.date(2026, 4, 20), "end_date": datetime.date(2026, 4, 23), "usage_limit": 30},
    {"name": "Giảm 8% Thành Viên",     "code": "MEMBER8",  "discount_percent":  8, "min_order_value": 150000,  "start_date": datetime.date(2026, 3,  1), "end_date": datetime.date(2026, 5, 31), "usage_limit": 200},
    {"name": "Giảm 12% Cuối Tuần",     "code": "WEEKEND12","discount_percent": 12, "min_order_value": 250000,  "start_date": datetime.date(2026, 4, 18), "end_date": datetime.date(2026, 4, 19), "usage_limit": 60},
    {"name": "Giảm 25% Siêu VIP",      "code": "SVIP25",   "discount_percent": 25, "min_order_value": 800000,  "start_date": datetime.date(2026, 4,  1), "end_date": datetime.date(2026, 6, 30), "usage_limit": 20},
    {"name": "Giảm 30% Clearance",     "code": "CLEAR30",  "discount_percent": 30, "min_order_value": 600000,  "start_date": datetime.date(2026, 4, 15), "end_date": datetime.date(2026, 4, 25), "usage_limit": 40},
    {"name": "Giảm 6% Đơn Đầu",        "code": "FIRST6",   "discount_percent":  6, "min_order_value": 100000,  "start_date": datetime.date(2026, 1,  1), "end_date": datetime.date(2026,12, 31), "usage_limit": None},
    {"name": "Giảm 18% Tri Ân",        "code": "THANKS18", "discount_percent": 18, "min_order_value": 350000,  "start_date": datetime.date(2026, 6,  1), "end_date": datetime.date(2026, 6, 15), "usage_limit": 75},
]

RETURN_REASONS = ["wrong_item", "damaged", "not_as_described", "changed_mind", "other"]
RETURN_DESCRIPTIONS = [
    "Sản phẩm nhận được khác với mô tả.",
    "Hàng bị lỗi, đường may không đều.",
    "Màu sắc khác so với ảnh.",
    "Tôi đặt nhầm size.",
    "Sản phẩm bị rách khi nhận.",
]


def _random_dt() -> datetime.datetime:
    return DATE_START + datetime.timedelta(seconds=random.randint(0, DATE_RANGE_SECONDS))


class Command(BaseCommand):
    help = "Seed full: variants, orders, reviews, promotions, discount codes, return requests"

    def handle(self, *args, **kwargs):
        Product.objects.all().update(sold_count=0, rating=0)

        users = list(User.objects.all())
        variants = list(ProductVariant.objects.select_related("product").all())

        if not users:
            self.stdout.write(self.style.ERROR("❌ Không có user nào"))
            return
        if not variants:
            self.stdout.write(self.style.ERROR("❌ Không có product nào"))
            return

        # ── Phase 0: Seed Promotions + DiscountCodes ────────────────────────
        self.stdout.write("⏳ Phase 0: Seed Promotions + DiscountCodes...")
        promotions = self._seed_promotions()
        discount_codes = self._seed_discount_codes()
        self.stdout.write(f"  ✔ {len(promotions)} promotions, {len(discount_codes)} discount codes")

        # ── Phase 1: completed orders + reviews theo từng variant ───────────
        self.stdout.write(f"⏳ Phase 1: Seed completed orders + reviews ({len(variants)} variants)...")
        for i, variant in enumerate(variants, 1):
            self._ensure_completed_orders_and_reviews(variant, users)
            if i % 20 == 0:
                self.stdout.write(f"  ...{i}/{len(variants)} variants xong")

        # ── Phase 2: đơn hàng theo trạng thái ──────────────────────────────
        self.stdout.write(f"⏳ Phase 2: Seed đơn theo trạng thái ({len(EXTRA_STATUSES)} x {EXTRA_ORDERS_PER_STATUS})...")
        for status in EXTRA_STATUSES:
            self._seed_orders_by_status(status, variants, users)
            self.stdout.write(f"  ✔ {status}: {EXTRA_ORDERS_PER_STATUS} đơn xong")

        # ── Phase 3: đơn có mã giảm giá ────────────────────────────────────
        self.stdout.write(f"⏳ Phase 3: Seed {DISCOUNTED_ORDERS_COUNT} đơn có mã giảm giá...")
        self._seed_discounted_orders(variants, users, discount_codes)
        self.stdout.write(f"  ✔ {DISCOUNTED_ORDERS_COUNT} đơn giảm giá xong")

        # ── Phase 4: return requests ────────────────────────────────────────
        self.stdout.write(f"⏳ Phase 4: Seed {RETURN_REQUESTS_COUNT} return requests...")
        self._seed_return_requests(users)
        self.stdout.write(f"  ✔ {RETURN_REQUESTS_COUNT} return requests xong")

        self.stdout.write(self.style.SUCCESS("✅ Seed data xong!"))

    # ── Phase 0 ─────────────────────────────────────────────────────────────
    def _seed_promotions(self):
        result = []
        for data in PROMOTION_DATA:
            obj, _ = Promotion.objects.get_or_create(
                name=data["name"],
                defaults={
                    "discount_percent": data["discount_percent"],
                    "start_date": data["start_date"],
                    "end_date": data["end_date"],
                },
            )
            result.append(obj)
        return result

    def _seed_discount_codes(self):
        result = []
        for data in DISCOUNT_CODE_DATA:
            obj, _ = DiscountCode.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "discount_percent": data["discount_percent"],
                    "min_order_value": data["min_order_value"],
                    "start_date": data["start_date"],
                    "end_date": data["end_date"],
                    "is_active": True,
                    "usage_limit": data["usage_limit"],
                    "used_count": 0,
                },
            )
            result.append(obj)
        return result

    # ── Phase 1 ─────────────────────────────────────────────────────────────
    def _ensure_completed_orders_and_reviews(self, product, users):
        existing_items = (
            OrderItem.objects
            .filter(product=product, order__status="completed")
            .select_related("order__user")
        )
        buyer_map = {}
        for item in existing_items:
            uid = item.order.user_id
            if uid not in buyer_map:
                buyer_map[uid] = item.order

        need_orders = max(0, 5 - len(buyer_map))
        available_users = [u for u in users if u.id not in buyer_map]
        if not available_users:
            available_users = users

        for _ in range(need_orders):
            user = random.choice(available_users)
            order = self._create_order(user, product, status="completed")
            buyer_map[user.id] = order
            available_users = [u for u in available_users if u.id != user.id] or available_users

        reviewed_user_ids = set(
            Review.objects.filter(product=product).values_list("user_id", flat=True)
        )
        buyers_without_review = [
            (uid, order)
            for uid, order in buyer_map.items()
            if uid not in reviewed_user_ids
        ]
        need_reviews = max(0, 5 - Review.objects.filter(product=product).count())
        for uid, order in buyers_without_review[:need_reviews]:
            Review.objects.create(
                user=order.user,
                product=product,
                rating=random.randint(4, 5),
                content=random.choice(COMMENTS),
                feedback_type=random.choice(["quality", "price", "shipping"]),
            )

        self._update_product_stats(product)

    # ── Phase 2 ─────────────────────────────────────────────────────────────
    def _seed_orders_by_status(self, status, variants, users):
        existing = Order.objects.filter(status=status).count()
        need = max(0, EXTRA_ORDERS_PER_STATUS - existing)
        for _ in range(need):
            user = random.choice(users)
            variant = random.choice(variants)
            self._create_order(user, variant, status=status)

    # ── Phase 3 ─────────────────────────────────────────────────────────────
    def _seed_discounted_orders(self, variants, users, discount_codes):
        existing = Order.objects.filter(discount_code__isnull=False).count()
        need = max(0, DISCOUNTED_ORDERS_COUNT - existing)

        statuses = ["completed", "pending", "shipping", "awaiting_confirmation", "cancelled"]

        # ✅ Track used_count trong memory để tránh query DB mỗi vòng lặp
        usage_tracker = {
            code.pk: code.used_count for code in discount_codes
        }

        created = 0
        attempts = 0
        max_attempts = need * 10  # tránh infinite loop nếu tất cả code hết lượt

        while created < need and attempts < max_attempts:
            attempts += 1

            # ✅ Lọc ra các code còn lượt dùng
            available_codes = [
                code for code in discount_codes
                if code.usage_limit is None
                or usage_tracker[code.pk] < code.usage_limit
            ]

            if not available_codes:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Tất cả mã giảm giá đã hết lượt, chỉ tạo được {created}/{need} đơn"
                ))
                break

            user = random.choice(users)
            variant = random.choice(variants)
            discount_code = random.choice(available_codes)
            status = random.choice(statuses)

            price = variant.get_price() or 100000
            qty = random.randint(1, 3)
            subtotal = Decimal(price * qty)
            shipping_fee = Decimal(30000)

            # ✅ Chỉ apply discount nếu đủ min_order_value
            discount_amount = Decimal(0)
            if subtotal >= discount_code.min_order_value:
                discount_amount = (
                    subtotal * Decimal(discount_code.discount_percent) / Decimal(100)
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

            total_price = max(subtotal + shipping_fee - discount_amount, Decimal(0))

            payment_method = random.choice(["cod", "wallet", "momo", "zalopay", "vnpay"])
            if payment_method == "cod":
                gateway_status = "none"
            elif status == "cancelled":
                gateway_status = random.choice(["failed", "pending"])
            elif status == "pending":
                gateway_status = "pending"
            else:
                gateway_status = "paid"

            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                discount_code=discount_code,
                discount_code_snapshot=discount_code.code,
                discount_amount=discount_amount,
                total_price=total_price,
                status=status,
                payment_method=payment_method,
                gateway_status=gateway_status,
            )
            OrderItem.objects.create(
                order=order,
                product=variant,
                quantity=qty,
                price=price,
            )
            Shipping.objects.create(
                order=order,
                name=user.username,
                phone="0123456789",
                address="TP.HCM",
                note="",
            )
            Order.objects.filter(pk=order.pk).update(created_at=_random_dt())

            # ✅ Cập nhật cả memory tracker lẫn DB
            usage_tracker[discount_code.pk] += 1
            DiscountCode.objects.filter(pk=discount_code.pk).update(
                used_count=F("used_count") + 1
            )

            created += 1

        self.stdout.write(f"  ✔ Đã tạo {created} đơn có mã giảm giá")
    # ── Phase 4 ─────────────────────────────────────────────────────────────
    def _seed_return_requests(self, users):
        existing = ReturnRequest.objects.count()
        need = max(0, RETURN_REQUESTS_COUNT - existing)

        # Lấy các completed order chưa có return request
        completed_orders = list(
            Order.objects
            .filter(status="completed")
            .filter(return_requests__isnull=True)
            .select_related("user")[:need * 2]  # lấy dư để có đủ chọn
        )

        if not completed_orders:
            self.stdout.write(self.style.WARNING("  ⚠ Không đủ completed order để tạo return request"))
            return

        for order in random.sample(completed_orders, min(need, len(completed_orders))):
            ReturnRequest.objects.create(
                order=order,
                user=order.user,
                reason=random.choice(RETURN_REASONS),
                description=random.choice(RETURN_DESCRIPTIONS),
                status="pending",  # chờ admin duyệt
            )

    # ── Shared helpers ───────────────────────────────────────────────────────
    def _create_order(self, user, product, status):
        price = product.get_price() or 100000
        qty = random.randint(1, 2)
        subtotal = price * qty
        shipping_fee = 30000

        payment_method = random.choice(["cod", "wallet", "momo", "zalopay", "vnpay"])
        if payment_method == "cod":
            gateway_status = "none"
        elif status == "cancelled":
            gateway_status = random.choice(["failed", "pending"])
        elif status == "pending":
            gateway_status = "pending"
        else:
            gateway_status = "paid"

        order = Order.objects.create(
            user=user,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total_price=subtotal + shipping_fee,
            status=status,
            payment_method=payment_method,
            gateway_status=gateway_status,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=price,
        )
        Shipping.objects.create(
            order=order,
            name=user.username,
            phone="0123456789",
            address="TP.HCM",
            note="",
        )
        Order.objects.filter(pk=order.pk).update(created_at=_random_dt())
        return order

    def _update_product_stats(self, variant):
        total_sold = (
            OrderItem.objects
            .filter(product=variant, order__status="completed")
            .aggregate(total=Sum("quantity"))
        )["total"] or 0

        avg_rating = (
            Review.objects
            .filter(product__product_id=variant.product_id, is_visible=True)
            .aggregate(avg=Avg("rating"))
        )["avg"] or 0

        Product.objects.filter(id=variant.product_id).update(
            sold_count=F("sold_count") + total_sold,
            rating=round(avg_rating, 2),
        )