"""ZaloPay Payment Gateway v2 — create order + verify callback (HMAC SHA256)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Một session tái sử dụng TCP/TLS tới sb-openapi — giảm độ trễ so với mỗi lần POST tạo kết nối mới.
_http = requests.Session()


def _hmac_sha256_hex(key: str, raw: str) -> str:
    return hmac.new(key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _backend_base(request) -> str:
    base = (getattr(settings, "BACKEND_PUBLIC_BASE", None) or "").strip().rstrip("/")
    if base:
        return base
    return request.build_absolute_uri("/").rstrip("/")


def _frontend_orders_url(**params: str) -> str:
    base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    q = urlencode(params)
    return f"{base}/orders?{q}" if q else f"{base}/orders"


def _frontend_wallet_url(**params: str) -> str:
    base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    q = urlencode(params)
    return f"{base}/dashboard/wallet?{q}" if q else f"{base}/dashboard/wallet"


def build_app_trans_id(order_id: int) -> str:
    """yymmdd_orderId_random — tối đa 40 ký tự (ZaloPay)."""
    prefix = datetime.now(_VN_TZ).strftime("%y%m%d")
    suffix = secrets.token_hex(3)
    raw = f"{prefix}_{order_id}_{suffix}"
    return raw[:40]


def prefer_zalopay_qr_gateway_url(order_url: str) -> str:
    """
    Chuẩn hóa về /pay/v2/qr?order=... trên domain ZaloPay — QR hiển thị trên cổng ZaloPay,
    không nhúng trên site merchant (theo luồng qcgateway).
    """
    raw = (order_url or "").strip()
    if not raw:
        return raw
    try:
        u = urlparse(raw)
        host = (u.netloc or "").lower()
        if "zalopay.vn" not in host:
            return raw
        segs = [s for s in (u.path or "").split("/") if s]
        if len(segs) < 3 or segs[0] != "pay" or segs[1] != "v2":
            return raw
        if segs[2] == "qr":
            return raw
        new_path = "/pay/v2/qr"
        return urlunparse((u.scheme, u.netloc, new_path, u.params, u.query, u.fragment))
    except Exception:
        return raw


def parse_order_id_from_app_trans_id(app_trans_id: str | None) -> int | None:
    s = str(app_trans_id or "").strip()
    parts = s.split("_")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None


def build_app_trans_id_for_wallet(wallet_tx_id: int) -> str:
    """yymmdd_w{wallet_tx_id}_hex — không trùng định dạng đơn hàng (phần giữa là số)."""
    prefix = datetime.now(_VN_TZ).strftime("%y%m%d")
    suffix = secrets.token_hex(2)
    raw = f"{prefix}_w{wallet_tx_id}_{suffix}"
    return raw[:40]


def parse_wallet_tx_id_from_app_trans_id(app_trans_id: str | None) -> int | None:
    s = str(app_trans_id or "").strip()
    parts = s.split("_")
    if len(parts) < 2:
        return None
    mid = parts[1]
    if len(mid) < 2 or mid[0].lower() != "w":
        return None
    rest = mid[1:]
    if not rest.isdigit():
        return None
    return int(rest)


def _create_mac_input(
    app_id: int,
    app_trans_id: str,
    app_user: str,
    amount: int,
    app_time: int,
    embed_data: str,
    item: str,
) -> str:
    return "|".join(
        (
            str(app_id),
            str(app_trans_id),
            str(app_user),
            str(amount),
            str(app_time),
            str(embed_data),
            str(item),
        )
    )


def _query_mac_input(app_id: int, app_trans_id: str, key1: str) -> str:
    """Theo tài liệu Query order: app_id|app_trans_id|mac_key (key1)."""
    return f"{app_id}|{app_trans_id}|{key1}"


def create_payment(
    request,
    order_id: int,
    amount_vnd: Decimal,
    description: str,
    app_user: str,
) -> tuple[str, str]:
    """
    Gọi POST /v2/create, trả (order_url, app_trans_id).
    app_trans_id cần lưu DB để gọi /v2/query khi IPN callback không tới được merchant.
    """
    raw_app_id = (getattr(settings, "ZALOPAY_APP_ID", None) or "").strip()
    key1 = (getattr(settings, "ZALOPAY_KEY1", None) or "").strip()
    if not raw_app_id or not key1:
        raise ValueError("ZaloPay chưa cấu hình (ZALOPAY_APP_ID, ZALOPAY_KEY1).")

    try:
        app_id = int(raw_app_id)
    except ValueError as exc:
        raise ValueError("ZALOPAY_APP_ID không hợp lệ.") from exc

    endpoint = (getattr(settings, "ZALOPAY_CREATE_ENDPOINT", None) or "").strip() or (
        "https://sb-openapi.zalopay.vn/v2/create"
    )
    callback_path = getattr(settings, "ZALOPAY_CALLBACK_PATH", "/api/payments/zalopay/callback/").strip()
    if callback_path.startswith("http"):
        callback_url = callback_path
    else:
        if not callback_path.startswith("/"):
            callback_path = "/" + callback_path
        base = _backend_base(request)
        callback_url = f"{base}{callback_path}"

    app_trans_id = build_app_trans_id(order_id)
    app_time = int(datetime.now(_VN_TZ).timestamp() * 1000)
    amount = int(amount_vnd.quantize(Decimal("1")))
    au = (app_user or "guest").strip()[:50] or "guest"
    desc = (description or f"Thanh toan don hang #{order_id}")[:256]
    redirect = _frontend_orders_url(payment="pending", order_id=str(order_id))
    # Chỉ redirect sau thanh toán. Không ép preferred_payment_method=vietqr để order_url không
    # bị khóa thẳng /pay/v2/vietqr (cổng QC thường báo "PT không khả dụng" với merchant trial).
    # QR trên site vẫn mã hóa order_url theo tài liệu QR động ZaloPay.
    embed_data = json.dumps({"redirecturl": redirect}, separators=(",", ":"))
    item = "[]"

    mac = _hmac_sha256_hex(key1, _create_mac_input(app_id, app_trans_id, au, amount, app_time, embed_data, item))

    payload: dict[str, Any] = {
        "app_id": app_id,
        "app_user": au,
        "app_time": app_time,
        "amount": amount,
        "app_trans_id": app_trans_id,
        "embed_data": embed_data,
        "item": item,
        "description": desc,
        "bank_code": "",
        "callback_url": callback_url,
        "mac": mac,
    }

    try:
        r = _http.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=(5, 20))
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as e:
        logger.exception("ZaloPay create failed: %s", e)
        raise ValueError("Không kết nối được ZaloPay.") from e

    if int(body.get("return_code", -1)) != 1:
        msg = body.get("return_message") or body.get("sub_return_message") or "ZaloPay từ chối tạo đơn"
        raise ValueError(str(msg))

    order_url = body.get("order_url")
    if not order_url:
        raise ValueError("ZaloPay không trả order_url.")
    return prefer_zalopay_qr_gateway_url(str(order_url)), app_trans_id


def create_wallet_deposit_payment(
    request,
    wallet_tx_id: int,
    amount_vnd: Decimal,
    app_user: str,
) -> tuple[str, str]:
    """POST /v2/create nạp ví — app_trans_id dạng ..._w{id}_... để callback phân nhánh."""
    raw_app_id = (getattr(settings, "ZALOPAY_APP_ID", None) or "").strip()
    key1 = (getattr(settings, "ZALOPAY_KEY1", None) or "").strip()
    if not raw_app_id or not key1:
        raise ValueError("ZaloPay chưa cấu hình (ZALOPAY_APP_ID, ZALOPAY_KEY1).")

    try:
        app_id = int(raw_app_id)
    except ValueError as exc:
        raise ValueError("ZALOPAY_APP_ID không hợp lệ.") from exc

    endpoint = (getattr(settings, "ZALOPAY_CREATE_ENDPOINT", None) or "").strip() or (
        "https://sb-openapi.zalopay.vn/v2/create"
    )
    callback_path = getattr(settings, "ZALOPAY_CALLBACK_PATH", "/api/payments/zalopay/callback/").strip()
    if callback_path.startswith("http"):
        callback_url = callback_path
    else:
        if not callback_path.startswith("/"):
            callback_path = "/" + callback_path
        base = _backend_base(request)
        callback_url = f"{base}{callback_path}"

    app_trans_id = build_app_trans_id_for_wallet(wallet_tx_id)
    app_time = int(datetime.now(_VN_TZ).timestamp() * 1000)
    amount = int(amount_vnd.quantize(Decimal("1")))
    au = (app_user or "guest").strip()[:50] or "guest"
    desc = (f"Nap tien vi #{wallet_tx_id}")[:256]
    redirect = _frontend_wallet_url(payment="pending", deposit_tx=str(wallet_tx_id))
    embed_data = json.dumps({"redirecturl": redirect}, separators=(",", ":"))
    item = "[]"

    mac = _hmac_sha256_hex(key1, _create_mac_input(app_id, app_trans_id, au, amount, app_time, embed_data, item))

    payload: dict[str, Any] = {
        "app_id": app_id,
        "app_user": au,
        "app_time": app_time,
        "amount": amount,
        "app_trans_id": app_trans_id,
        "embed_data": embed_data,
        "item": item,
        "description": desc,
        "bank_code": "",
        "callback_url": callback_url,
        "mac": mac,
    }

    try:
        r = _http.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=(5, 20))
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as e:
        logger.exception("ZaloPay create wallet failed: %s", e)
        raise ValueError("Không kết nối được ZaloPay.") from e

    if int(body.get("return_code", -1)) != 1:
        msg = body.get("return_message") or body.get("sub_return_message") or "ZaloPay từ chối tạo đơn"
        raise ValueError(str(msg))

    order_url = body.get("order_url")
    if not order_url:
        raise ValueError("ZaloPay không trả order_url.")
    return prefer_zalopay_qr_gateway_url(str(order_url)), app_trans_id


def query_order_status(app_trans_id: str) -> dict[str, Any]:
    """
    POST /v2/query — đối soát trạng thái thanh toán (bù khi callback lỗi mạng / localhost).
    https://docs.zalopay.vn/docs/specs/order-query/
    """
    raw_app_id = (getattr(settings, "ZALOPAY_APP_ID", None) or "").strip()
    key1 = (getattr(settings, "ZALOPAY_KEY1", None) or "").strip()
    if not raw_app_id or not key1:
        raise ValueError("ZaloPay chưa cấu hình (ZALOPAY_APP_ID, ZALOPAY_KEY1).")
    try:
        app_id = int(raw_app_id)
    except ValueError as exc:
        raise ValueError("ZALOPAY_APP_ID không hợp lệ.") from exc

    atid = (app_trans_id or "").strip()
    if not atid:
        raise ValueError("Thiếu app_trans_id.")

    endpoint = (getattr(settings, "ZALOPAY_QUERY_ENDPOINT", None) or "").strip() or (
        "https://sb-openapi.zalopay.vn/v2/query"
    )
    mac = _hmac_sha256_hex(key1, _query_mac_input(app_id, atid, key1))
    payload: dict[str, Any] = {"app_id": app_id, "app_trans_id": atid, "mac": mac}

    try:
        r = _http.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=(5, 20))
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        logger.exception("ZaloPay query failed: %s", e)
        raise ValueError("Không kết nối được ZaloPay (query).") from e


def is_query_result_paid(amount_vnd: Decimal, body: dict[str, Any]) -> tuple[bool, str]:
    """
    return_code == 1 và có zp_trans_id coi là đã thanh toán; đối chiếu amount nếu ZaloPay trả.
    """
    if int(body.get("return_code", -1)) != 1:
        return False, ""
    zp = body.get("zp_trans_id")
    if zp is None or str(zp).strip() == "":
        return False, ""
    expected = int(amount_vnd.quantize(Decimal("1")))
    raw_amt = body.get("amount")
    if raw_amt is not None and str(raw_amt).strip() != "":
        try:
            if int(raw_amt) != expected:
                logger.warning("ZaloPay query amount mismatch: got %s expected %s", raw_amt, expected)
                return False, ""
        except (TypeError, ValueError):
            pass
    return True, str(zp).strip()


def verify_callback_mac(data_str: str, received_mac: str) -> bool:
    key2 = (getattr(settings, "ZALOPAY_KEY2", None) or "").strip()
    if not key2 or not data_str or not received_mac:
        return False
    expected = _hmac_sha256_hex(key2, data_str)
    return hmac.compare_digest(expected, received_mac.strip())


def parse_callback_payload(data_str: str) -> dict[str, Any]:
    return json.loads(data_str)


def callback_inner_get(inner: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in inner and inner[k] is not None:
            return inner[k]
    return None
