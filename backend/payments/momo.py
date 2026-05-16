"""MoMo Payment Gateway v2 — create request + verify notify (HMAC SHA256)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _hmac_sha256(secret: str, raw: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _backend_base(request) -> str:
    base = (getattr(settings, "BACKEND_PUBLIC_BASE", None) or "").strip().rstrip("/")
    if base:
        return base
    return request.build_absolute_uri("/").rstrip("/")


def create_payment(request, order_id: int, amount_vnd: Decimal, order_info: str) -> str:
    """Gọi API create (payWithMethod — collection link — hoặc captureWallet), trả về payUrl."""
    partner = (getattr(settings, "MOMO_PARTNER_CODE", None) or "").strip()
    access = (getattr(settings, "MOMO_ACCESS_KEY", None) or "").strip()
    secret = (getattr(settings, "MOMO_SECRET_KEY", None) or "").strip()
    endpoint = (getattr(settings, "MOMO_ENDPOINT", None) or "").strip() or "https://test-payment.momo.vn/v2/gateway/api/create"
    request_type = (getattr(settings, "MOMO_REQUEST_TYPE", None) or "payWithMethod").strip() or "payWithMethod"

    if not partner or not access or not secret:
        raise ValueError("MoMo chưa cấu hình (MOMO_PARTNER_CODE, MOMO_ACCESS_KEY, MOMO_SECRET_KEY).")

    base = _backend_base(request)
    return_path = getattr(settings, "MOMO_RETURN_PATH", "/api/payments/momo/return/")
    ipn_path = getattr(settings, "MOMO_IPN_PATH", "/api/payments/momo/notify/")
    redirect_url = f"{base}{return_path}"
    ipn_url = f"{base}{ipn_path}"

    request_id = str(uuid.uuid4())
    order_id_str = f"FS{order_id}_{int(time.time())}"
    amount = int(amount_vnd.quantize(Decimal("1")))
    extra_data = ""
    order_info_s = (order_info or f"Thanh toan don hang #{order_id}")[:255]
    partner_name = getattr(settings, "MOMO_PARTNER_NAME", "FashionStore")
    store_id = getattr(settings, "MOMO_STORE_ID", "FashionStore")

    # Cùng chuỗi ký HMAC với sample collection_link / MoMo.py (requestType nằm trong raw)
    raw_sig = (
        f"accessKey={access}"
        f"&amount={amount}"
        f"&extraData={extra_data}"
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id_str}"
        f"&orderInfo={order_info_s}"
        f"&partnerCode={partner}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType={request_type}"
    )
    signature = _hmac_sha256(secret, raw_sig)

    # Body giống collection_link.py khi payWithMethod; captureWallet giữ payload tối giản
    if request_type == "payWithMethod":
        payload = {
            "partnerCode": partner,
            "orderId": order_id_str,
            "partnerName": partner_name,
            "storeId": store_id,
            "ipnUrl": ipn_url,
            "amount": amount,
            "lang": "vi",
            "requestType": request_type,
            "redirectUrl": redirect_url,
            "autoCapture": getattr(settings, "MOMO_AUTO_CAPTURE", True),
            "orderInfo": order_info_s,
            "requestId": request_id,
            "extraData": extra_data,
            "signature": signature,
            "orderGroupId": getattr(settings, "MOMO_ORDER_GROUP_ID", "") or "",
        }
    else:
        payload = {
            "partnerCode": partner,
            "partnerName": partner_name,
            "storeId": store_id,
            "requestId": request_id,
            "amount": amount,
            "orderId": order_id_str,
            "orderInfo": order_info_s,
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "extraData": extra_data,
            "requestType": request_type,
            "signature": signature,
        }

    try:
        r = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as e:
        logger.exception("MoMo create failed: %s", e)
        raise ValueError("Không kết nối được MoMo.") from e

    if int(body.get("resultCode", -1)) != 0:
        msg = body.get("message") or body.get("localMessage") or "MoMo từ chối giao dịch"
        raise ValueError(str(msg))

    pay_url = body.get("payUrl")
    if not pay_url:
        raise ValueError("MoMo không trả payUrl.")
    return str(pay_url)


def create_wallet_payment(request, wallet_tx_id: int, amount_vnd: Decimal) -> tuple[str, str]:
    """
    Tạo phiên thanh toán MoMo nạp ví. orderId dạng WALLET{transaction_id}_{ts} (không trùng FS{order_id}).
    Trả (payUrl, orderId).
    """
    partner = (getattr(settings, "MOMO_PARTNER_CODE", None) or "").strip()
    access = (getattr(settings, "MOMO_ACCESS_KEY", None) or "").strip()
    secret = (getattr(settings, "MOMO_SECRET_KEY", None) or "").strip()
    endpoint = (getattr(settings, "MOMO_ENDPOINT", None) or "").strip() or "https://test-payment.momo.vn/v2/gateway/api/create"
    request_type = (getattr(settings, "MOMO_REQUEST_TYPE", None) or "payWithMethod").strip() or "payWithMethod"

    if not partner or not access or not secret:
        raise ValueError("MoMo chưa cấu hình (MOMO_PARTNER_CODE, MOMO_ACCESS_KEY, MOMO_SECRET_KEY).")

    base = _backend_base(request)
    return_path = getattr(settings, "MOMO_RETURN_PATH", "/api/payments/momo/return/")
    ipn_path = getattr(settings, "MOMO_IPN_PATH", "/api/payments/momo/notify/")
    redirect_url = f"{base}{return_path}"
    ipn_url = f"{base}{ipn_path}"

    request_id = str(uuid.uuid4())
    order_id_str = f"WALLET{wallet_tx_id}_{int(time.time())}"
    amount = int(amount_vnd.quantize(Decimal("1")))
    extra_data = ""
    order_info_s = (f"Nap tien vi #{wallet_tx_id}")[:255]
    partner_name = getattr(settings, "MOMO_PARTNER_NAME", "FashionStore")
    store_id = getattr(settings, "MOMO_STORE_ID", "FashionStore")

    raw_sig = (
        f"accessKey={access}"
        f"&amount={amount}"
        f"&extraData={extra_data}"
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id_str}"
        f"&orderInfo={order_info_s}"
        f"&partnerCode={partner}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType={request_type}"
    )
    signature = _hmac_sha256(secret, raw_sig)

    if request_type == "payWithMethod":
        payload = {
            "partnerCode": partner,
            "orderId": order_id_str,
            "partnerName": partner_name,
            "storeId": store_id,
            "ipnUrl": ipn_url,
            "amount": amount,
            "lang": "vi",
            "requestType": request_type,
            "redirectUrl": redirect_url,
            "autoCapture": getattr(settings, "MOMO_AUTO_CAPTURE", True),
            "orderInfo": order_info_s,
            "requestId": request_id,
            "extraData": extra_data,
            "signature": signature,
            "orderGroupId": getattr(settings, "MOMO_ORDER_GROUP_ID", "") or "",
        }
    else:
        payload = {
            "partnerCode": partner,
            "partnerName": partner_name,
            "storeId": store_id,
            "requestId": request_id,
            "amount": amount,
            "orderId": order_id_str,
            "orderInfo": order_info_s,
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "extraData": extra_data,
            "requestType": request_type,
            "signature": signature,
        }

    try:
        r = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as e:
        logger.exception("MoMo create wallet failed: %s", e)
        raise ValueError("Không kết nối được MoMo.") from e

    if int(body.get("resultCode", -1)) != 0:
        msg = body.get("message") or body.get("localMessage") or "MoMo từ chối giao dịch"
        raise ValueError(str(msg))

    pay_url = body.get("payUrl")
    if not pay_url:
        raise ValueError("MoMo không trả payUrl.")
    return str(pay_url), order_id_str


def verify_notify_signature(body: dict[str, Any]) -> bool:
    """Xác thực chữ ký webhook MoMo (partnerCode, orderId, requestId, amount, orderInfo, orderType, transId, resultCode, message, payType, responseTime, extraData, signature)."""
    secret = (getattr(settings, "MOMO_SECRET_KEY", None) or "").strip()
    if not secret:
        return False

    received = (body.get("signature") or "").strip()
    if not received:
        return False

    access = (getattr(settings, "MOMO_ACCESS_KEY", None) or "").strip()
    if not access:
        return False

    amount = body.get("amount")
    extra_data = body.get("extraData") or ""
    message = body.get("message") or ""
    order_id = body.get("orderId") or ""
    order_info = body.get("orderInfo") or ""
    order_type = body.get("orderType") or ""
    partner = body.get("partnerCode") or ""
    pay_type = body.get("payType") or ""
    request_id = body.get("requestId") or ""
    response_time = body.get("responseTime") or ""
    result_code = body.get("resultCode")
    trans_id = body.get("transId") or ""

    raw = (
        f"accessKey={access}"
        f"&amount={amount}"
        f"&extraData={extra_data}"
        f"&message={message}"
        f"&orderId={order_id}"
        f"&orderInfo={order_info}"
        f"&orderType={order_type}"
        f"&partnerCode={partner}"
        f"&payType={pay_type}"
        f"&requestId={request_id}"
        f"&responseTime={response_time}"
        f"&resultCode={result_code if result_code is not None else ''}"
        f"&transId={trans_id}"
    )
    expected = _hmac_sha256(secret, raw)
    return hmac.compare_digest(expected, received)


def parse_order_id_from_momo(order_id_str: str) -> int | None:
    s = str(order_id_str or "")
    if s.startswith("WALLET"):
        return None
    if s.startswith("FS"):
        s2 = s[2:]
        if "_" in s2:
            s2 = s2.split("_")[0]
        if s2.isdigit():
            return int(s2)
    return None


def parse_wallet_tx_id_from_momo(order_id_str: str | None) -> int | None:
    s = str(order_id_str or "").strip()
    if not s.startswith("WALLET"):
        return None
    rest = s[6:]
    head = rest.split("_", 1)[0] if rest else ""
    if head.isdigit():
        return int(head)
    return None
