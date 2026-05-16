"""VNPay querydr by order id (vnp_TxnRef = FS{id})."""

from __future__ import annotations

import json
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError

from orders.models import Order
from payments import vnpay

_VNP_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class Command(BaseCommand):
    help = "Call VNPay querydr. Use --trans-date=vnp_PayDate (yyyyMMddHHmmss); default uses order created_at (may not match)."

    def add_arguments(self, parser):
        parser.add_argument("order_id", type=int, help="Order PK (TxnRef FS{id})")
        parser.add_argument(
            "--trans-date",
            type=str,
            default="",
            help="vnp_TransactionDate yyyyMMddHHmmss",
        )

    def handle(self, *args, **options):
        oid = options["order_id"]
        try:
            order = Order.objects.get(pk=oid)
        except Order.DoesNotExist as e:
            raise CommandError(f"Order {oid} not found") from e

        if order.payment_method != "vnpay":
            raise CommandError("Order is not VNPay.")

        txn_ref = vnpay.txn_ref_for_order(oid)
        trans_date = (options.get("trans_date") or "").strip()
        if not trans_date:
            trans_date = order.created_at.astimezone(_VNP_TZ).strftime("%Y%m%d%H%M%S")
            self.stdout.write(
                self.style.WARNING(
                    f"Using order.created_at as trans-date: {trans_date} "
                    "(if API errors, pass --trans-date from vnp_PayDate)"
                )
            )

        try:
            out = vnpay.query_dr(txn_ref=txn_ref, transaction_date=trans_date)
        except ValueError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
