from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Order
from orders.constants import RETURN_WINDOW


class Command(BaseCommand):
    help = "Log các đơn hàng đã hết cửa sổ hoàn trả."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ in ra kết quả, không thực hiện thao tác nào.",
        )

    def handle(self, *args, **options):
        deadline = timezone.now() - RETURN_WINDOW

        qs = Order.objects.filter(
            status="completed",
            confirmed_by_user=True,
            completed_at__lt=deadline,
        ).exclude(
            return_requests__status__in=("pending", "approved")
        )

        count = qs.count()
        mode = "[DRY RUN] " if options["dry_run"] else ""
        self.stdout.write(f"{mode}Tìm thấy {count} đơn hết hạn hoàn trả.")
        if options["dry_run"]:
            for order in qs[:10]:  # preview tối đa 10 đơn
                self.stdout.write(f"  - Đơn #{order.id}, completed_at={order.completed_at}")
        self.stdout.write(self.style.SUCCESS(f"{mode}Hoàn tất."))