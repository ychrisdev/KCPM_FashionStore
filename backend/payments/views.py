"""Return / IPN / Notify cho VNPay, MoMo và ZaloPay."""

from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import momo, vnpay, zalopay
from .services import mark_order_paid, mark_order_payment_failed

logger = logging.getLogger(__name__)


def _vnpay_guard_order(order_id: int):
    """Trả (order, None) nếu hợp lệ; (None, 'missing'|'wrong_method')."""
    from orders.models import Order

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return None, "missing"
    if order.payment_method != "vnpay":
        logger.warning("VNPay callback payment_method mismatch order=%s", order_id)
        return None, "wrong_method"
    return order, None


def _frontend_orders_url(**params) -> str:
    base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    q = urlencode(params)
    return f"{base}/orders?{q}" if q else f"{base}/orders"


def _frontend_wallet_url(**params) -> str:
    base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    q = urlencode(params)
    return f"{base}/dashboard/wallet?{q}" if q else f"{base}/dashboard/wallet"


class VnpayReturnView(View):
    """Trình duyệt quay lại sau thanh toán VNPay."""

    def get(self, request):
        from decimal import Decimal

        ok, info = vnpay.verify_callback(request.GET)
        oid = info.get("order_id")
        if ok and oid:
            order, vnp_err = _vnpay_guard_order(oid)
            if vnp_err == "missing":
                return HttpResponseRedirect(_frontend_orders_url(payment="failed", reason="order"))
            if vnp_err == "wrong_method":
                return HttpResponseRedirect(_frontend_orders_url(payment="failed", order_id=oid))

            raw = info.get("raw") or {}
            vnp_amount = raw.get("vnp_Amount")
            if vnp_amount is not None and str(vnp_amount).strip() != "":
                try:
                    if int(str(vnp_amount)) != int(order.total_price.quantize(Decimal("1"))) * 100:
                        logger.warning("VNPay return amount mismatch order=%s", oid)
                except (TypeError, ValueError):
                    pass

            txn = str(info.get("transaction_no") or "")
            mark_order_paid(oid, txn)
            return HttpResponseRedirect(_frontend_orders_url(payment="success", order_id=oid))

        if oid and info.get("response_code") not in (None, "", "00"):
            mark_order_payment_failed(oid)
        fail_params: dict[str, str] = {"payment": "failed", "reason": str(info.get("reason") or "vnpay")}
        rc = str(info.get("response_code") or request.GET.get("vnp_ResponseCode") or "").strip()
        if rc:
            fail_params["vnp_rc"] = rc
        return HttpResponseRedirect(_frontend_orders_url(**fail_params))


class VnpayIpnView(View):
    """Server-to-server VNPay (GET query giống return)."""

    def get(self, request):
        from decimal import Decimal

        ok, info = vnpay.verify_callback(request.GET)
        oid = info.get("order_id")
        if info.get("reason") in ("missing_secret", "missing_hash", "bad_signature"):
            return HttpResponse(
                json.dumps({"RspCode": "97", "Message": "Fail"}),
                content_type="application/json",
                status=400,
            )
        if not oid:
            return HttpResponse(
                json.dumps({"RspCode": "97", "Message": "Fail"}),
                content_type="application/json",
                status=400,
            )
        if ok:
            order, vnp_err = _vnpay_guard_order(oid)
            if vnp_err == "missing":
                return HttpResponse(
                    json.dumps({"RspCode": "01", "Message": "Order not found"}),
                    content_type="application/json",
                )
            if vnp_err == "wrong_method":
                return HttpResponse(
                    json.dumps({"RspCode": "04", "Message": "Reject"}),
                    content_type="application/json",
                )
            raw = info.get("raw") or {}
            vnp_amount = raw.get("vnp_Amount")
            if vnp_amount is not None and str(vnp_amount).strip() != "":
                try:
                    if int(str(vnp_amount)) != int(order.total_price.quantize(Decimal("1"))) * 100:
                        logger.warning("VNPay IPN amount mismatch order=%s", oid)
                except (TypeError, ValueError):
                    pass
            txn = str(info.get("transaction_no") or "")
            mark_order_paid(oid, txn)
            return HttpResponse(
                json.dumps({"RspCode": "00", "Message": "Confirm Success"}),
                content_type="application/json",
            )
        return HttpResponse(
            json.dumps({"RspCode": "01", "Message": "Reject"}),
            content_type="application/json",
        )


@method_decorator(csrf_exempt, name="dispatch")
class MomoNotifyView(View):
    """Webhook MoMo (POST JSON)."""

    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("invalid json")

        if not momo.verify_notify_signature(body):
            logger.warning("MoMo notify bad signature")
            return HttpResponse(
                json.dumps({"status": 1, "message": "Bad signature"}),
                content_type="application/json",
                status=400,
            )

        from decimal import Decimal

        from wallets.services import complete_wallet_deposit, mark_wallet_deposit_failed

        wallet_tid = momo.parse_wallet_tx_id_from_momo(body.get("orderId"))
        if wallet_tid is not None:
            result = int(body.get("resultCode", -1))
            raw_amt = body.get("amount")
            amt: Decimal | None = None
            if raw_amt is not None and str(raw_amt).strip() != "":
                try:
                    amt = Decimal(str(raw_amt))
                except Exception:
                    amt = None
            if result == 0:
                if not complete_wallet_deposit(
                    wallet_tid,
                    gateway="momo",
                    external_ref=str(body.get("transId") or ""),
                    amount_vnd=amt,
                ):
                    logger.warning("MoMo notify wallet could not complete tx=%s", wallet_tid)
            else:
                mark_wallet_deposit_failed(wallet_tid)
            return HttpResponse(
                json.dumps({"status": 0, "message": "ok"}),
                content_type="application/json",
            )

        oid = momo.parse_order_id_from_momo(body.get("orderId"))
        if not oid:
            return HttpResponseBadRequest("bad orderId")

        result = int(body.get("resultCode", -1))
        if result == 0:
            trans_id = str(body.get("transId") or "")
            mark_order_paid(oid, trans_id)
        else:
            mark_order_payment_failed(oid)

        return HttpResponse(
            json.dumps({"status": 0, "message": "ok"}),
            content_type="application/json",
        )


class MomoReturnView(View):
    """Trình duyệt quay lại từ MoMo — không dùng cùng chữ ký webhook; xác minh đơn + resultCode."""

    def get(self, request):
        from decimal import Decimal

        from orders.models import Order
        from wallets.models import WalletTransaction
        from wallets.services import complete_wallet_deposit, mark_wallet_deposit_failed

        oid_raw = request.GET.get("orderId")
        wallet_tid = momo.parse_wallet_tx_id_from_momo(oid_raw)
        try:
            result = int(request.GET.get("resultCode", -1))
        except (TypeError, ValueError):
            result = -1

        if wallet_tid is not None:
            try:
                wtx = WalletTransaction.objects.get(pk=wallet_tid, type="deposit", gateway="momo")
            except WalletTransaction.DoesNotExist:
                return HttpResponseRedirect(_frontend_wallet_url(payment="failed"))

            raw_amount = request.GET.get("amount")
            if wtx.status == "pending":
                if raw_amount is not None and str(raw_amount).strip() != "":
                    try:
                        if Decimal(str(raw_amount)) != wtx.amount.quantize(Decimal("1")):
                            logger.warning("MoMo return wallet amount mismatch tx=%s", wallet_tid)
                    except Exception:
                        pass
                if result == 0:
                    amt = None
                    if raw_amount is not None and str(raw_amount).strip() != "":
                        try:
                            amt = Decimal(str(raw_amount))
                        except Exception:
                            amt = None
                    complete_wallet_deposit(
                        wallet_tid,
                        gateway="momo",
                        external_ref=str(request.GET.get("transId") or ""),
                        amount_vnd=amt,
                    )
                else:
                    mark_wallet_deposit_failed(wallet_tid)

            if result == 0:
                return HttpResponseRedirect(
                    _frontend_wallet_url(payment="success", deposit_tx=str(wallet_tid)),
                )
            return HttpResponseRedirect(
                _frontend_wallet_url(payment="failed", deposit_tx=str(wallet_tid)),
            )

        oid = momo.parse_order_id_from_momo(oid_raw)
        if not oid:
            return HttpResponseRedirect(_frontend_orders_url(payment="failed"))

        try:
            order = Order.objects.get(pk=oid)
        except Order.DoesNotExist:
            return HttpResponseRedirect(_frontend_orders_url(payment="failed"))

        if order.payment_method != "momo":
            return HttpResponseRedirect(_frontend_orders_url(payment="failed", order_id=oid))

        raw_amount = request.GET.get("amount")
        if raw_amount is not None and str(raw_amount).strip() != "":
            try:
                if Decimal(str(raw_amount)) != order.total_price.quantize(Decimal("1")):
                    logger.warning("MoMo return amount mismatch order=%s", oid)
            except Exception:
                pass

        if result == 0:
            mark_order_paid(oid, str(request.GET.get("transId") or ""))
            return HttpResponseRedirect(_frontend_orders_url(payment="success", order_id=oid))

        mark_order_payment_failed(oid)
        return HttpResponseRedirect(_frontend_orders_url(payment="failed", order_id=oid))


@method_decorator(csrf_exempt, name="dispatch")
class ZalopayCallbackView(View):
    """Webhook ZaloPay (POST JSON: data, mac)."""

    def post(self, request):
        from decimal import Decimal

        from orders.models import Order

        body: dict
        try:
            raw = request.body.decode("utf-8") or "{}"
            body = json.loads(raw) if raw.strip().startswith("{") else {}
        except json.JSONDecodeError:
            body = {}
        if not body and request.POST:
            body = {"data": request.POST.get("data"), "mac": request.POST.get("mac")}

        data_str = body.get("data")
        recv_mac = body.get("mac")
        if not isinstance(data_str, str) or not recv_mac:
            return JsonResponse({"return_code": 2, "return_message": "Missing data or mac"})

        if not zalopay.verify_callback_mac(data_str, str(recv_mac)):
            logger.warning("ZaloPay callback bad mac")
            return JsonResponse({"return_code": 2, "return_message": "Invalid MAC"})

        try:
            inner = zalopay.parse_callback_payload(data_str)
        except json.JSONDecodeError:
            return JsonResponse({"return_code": 2, "return_message": "Invalid data"})

        from wallets.models import WalletTransaction
        from wallets.services import complete_wallet_deposit

        app_trans_id = zalopay.callback_inner_get(inner, "app_trans_id", "apptransid")
        app_trans_id_str = str(app_trans_id or "")

        wid = zalopay.parse_wallet_tx_id_from_app_trans_id(app_trans_id_str)
        if wid is not None:
            try:
                wtx = WalletTransaction.objects.get(pk=wid, type="deposit", gateway="zalopay")
            except WalletTransaction.DoesNotExist:
                logger.warning("ZaloPay callback unknown wallet_tx=%s", wid)
                return JsonResponse({"return_code": 2, "return_message": "Txn not found"})

            raw_amt = zalopay.callback_inner_get(inner, "amount")
            if raw_amt is not None and str(raw_amt).strip() != "":
                try:
                    if int(raw_amt) != int(wtx.amount.quantize(Decimal("1"))):
                        logger.warning("ZaloPay callback amount mismatch wallet_tx=%s", wid)
                        return JsonResponse({"return_code": 2, "return_message": "Amount mismatch"})
                except (TypeError, ValueError):
                    pass

            zp = str(zalopay.callback_inner_get(inner, "zp_trans_id", "zptransid") or "")
            if zp:
                complete_wallet_deposit(
                    wid,
                    gateway="zalopay",
                    external_ref=zp,
                    amount_vnd=wtx.amount,
                )
            return JsonResponse({"return_code": 1, "return_message": "success"})

        oid = zalopay.parse_order_id_from_app_trans_id(app_trans_id_str)
        if not oid:
            return JsonResponse({"return_code": 2, "return_message": "Bad app_trans_id"})

        try:
            order = Order.objects.get(pk=oid)
        except Order.DoesNotExist:
            logger.warning("ZaloPay callback unknown order=%s", oid)
            return JsonResponse({"return_code": 2, "return_message": "Order not found"})

        if order.payment_method != "zalopay":
            logger.warning("ZaloPay callback payment_method mismatch order=%s", oid)
            return JsonResponse({"return_code": 2, "return_message": "Reject"})

        raw_amt = zalopay.callback_inner_get(inner, "amount")
        if raw_amt is not None and str(raw_amt).strip() != "":
            try:
                if int(raw_amt) != int(order.total_price.quantize(Decimal("1"))):
                    logger.warning("ZaloPay callback amount mismatch order=%s", oid)
                    return JsonResponse({"return_code": 2, "return_message": "Amount mismatch"})
            except (TypeError, ValueError):
                pass

        zp = str(zalopay.callback_inner_get(inner, "zp_trans_id", "zptransid") or "")
        mark_order_paid(oid, zp)
        return JsonResponse({"return_code": 1, "return_message": "success"})
