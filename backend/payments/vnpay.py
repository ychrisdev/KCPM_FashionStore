"""VNPay redirect (v2.1): build URL + verify callback (HMAC SHA512) + tra cứu querydr."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# VNPay bắt buộc GMT+7 cho vnp_CreateDate / vnp_ExpireDate (không dùng TIME_ZONE Django — project có thể để UTC).
_VNP_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Thông điệp ngắn (một số mã phổ biến — bảng đầy đủ trong tài liệu VNPay)
VNP_RESPONSE_HINT_VI: dict[str, str] = {
    "00": "Giao dịch thành công.",
    "07": "Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường).",
    "09": "Thẻ/Tài khoản chưa đăng ký Internet Banking.",
    "10": "Xác thực OTP sai.",
    "11": "Hết hạn xác thực OTP.",
    "12": "Thẻ bị khóa.",
    "13": "Nhập sai mật khẩu thanh toán quá số lần.",
    "24": "Giao dịch bị hủy.",
    "51": "Tài khoản không đủ số dư.",
    "65": "Vượt hạn mức giao dịch trong ngày.",
    "75": "Ngân hàng thanh toán đang bảo trì.",
    "79": "Nhập sai mật khẩu thanh toán quá số lần.",
    "15": "Hết thời gian chờ thanh toán.",
    "70": "Sai chữ ký (checksum). Kiểm tra cặp TMN + HashSecret; thử bỏ VNP_BANK_CODE, tắt VNP_SEND_EXPIRE_DATE.",
}


def vnp_response_hint_vi(code: str | None) -> str | None:
    if not code:
        return None
    c = str(code).strip()
    return VNP_RESPONSE_HINT_VI.get(c)


def _hmac_sha512(secret: str, msg: str) -> str:
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha512).hexdigest()


def _vnp_quote(value: str) -> str:
    """Giống PHP urlencode khi ký — khoảng trắng thành +."""
    return urllib.parse.quote_plus(str(value), safe="")


def _backend_base(request) -> str:
    base = (getattr(settings, "BACKEND_PUBLIC_BASE", None) or "").strip().rstrip("/")
    if base:
        return base
    return request.build_absolute_uri("/").rstrip("/")


def build_payment_url(request, order_id: int, amount_vnd: Decimal, order_info: str) -> str:
    """
    amount_vnd: tổng tiền đơn (VND), ví dụ Decimal('150000').
    """
    tmn = (getattr(settings, "VNP_TMN_CODE", None) or "").strip()
    secret = (getattr(settings, "VNP_HASH_SECRET", None) or "").strip()
    pay_url = (getattr(settings, "VNP_PAYMENT_URL", None) or "").strip() or "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    if not tmn or not secret:
        raise ValueError("VNPay chưa cấu hình (VNP_TMN_CODE, VNP_HASH_SECRET).")

    import time
    txn_ref = f"FS{order_id}_{int(time.time())}"
    base = _backend_base(request)
    return_path = getattr(settings, "VNP_RETURN_PATH", "/api/payments/vnpay/return/")
    return_url = f"{base}{return_path}"

    expire_minutes = int(getattr(settings, "VNP_EXPIRE_MINUTES", 30))
    now = datetime.now(_VNP_TZ)
    create_date = now.strftime("%Y%m%d%H%M%S")
    expire_date = (now + timedelta(minutes=expire_minutes)).strftime("%Y%m%d%H%M%S")
    send_expire = getattr(settings, "VNP_SEND_EXPIRE_DATE", False)

    ip_addr = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
        "REMOTE_ADDR", "127.0.0.1"
    )

    amount_int = int(amount_vnd * 100) if amount_vnd == int(amount_vnd) else int(amount_vnd.quantize(Decimal("1")) * 100)

    # vnp_OrderInfo: không dấu, không ký tự đặc biệt (tài liệu VNPay)
    raw_info = (order_info or f"Thanh toan don hang {order_id}")[:255]
    safe_order_info = "".join(c for c in raw_info if c.isalnum() or c in " -_.")

    # Không gửi vnp_IpnUrl trên URL pay — IPN cấu hình trên cổng VNPay / devreg (mẫu tích hợp không gửi trường này).

    vnp_params: dict[str, Any] = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": tmn,
        "vnp_Amount": str(amount_int),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": txn_ref,
        "vnp_OrderInfo": safe_order_info or f"Thanh toan don hang {order_id}",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url,
        "vnp_CreateDate": create_date,
        "vnp_IpAddr": ip_addr[:45],
    }
    if send_expire:
        vnp_params["vnp_ExpireDate"] = expire_date

    # VNPAYQR = cổng mở thẳng luồng quét QR (tài liệu VNPay); VNBANK / INTCARD = ATM / thẻ quốc tế
    bank_code = (getattr(settings, "VNP_BANK_CODE", None) or "").strip()
    if bank_code:
        vnp_params["vnp_BankCode"] = bank_code

    # Bỏ giá trị rỗng; sắp xếp key để ký (giống PHP ksort + urlencode từng phần)
    filtered = {k: v for k, v in vnp_params.items() if v is not None and str(v) != ""}
    sorted_keys = sorted(filtered.keys())
    sign_parts = []
    for k in sorted_keys:
        val = filtered[k]
        sign_parts.append(f"{k}={_vnp_quote(str(val))}")
    sign_data = "&".join(sign_parts)
    secure_hash = _hmac_sha512(secret, sign_data)

    query = urllib.parse.urlencode(filtered, quote_via=urllib.parse.quote_plus)
    full = f"{pay_url}?{query}&vnp_SecureHash={secure_hash}"
    return full


def verify_callback(query_dict) -> tuple[bool, dict[str, Any]]:
    """query_dict: request.GET (QueryDict) hoặc dict-like."""
    secret = (getattr(settings, "VNP_HASH_SECRET", None) or "").strip()
    if not secret:
        return False, {"reason": "missing_secret"}

    data = {}
    for key in query_dict.keys():
        if key in ("vnp_SecureHash", "vnp_SecureHashType"):
            continue
        if not str(key).startswith("vnp_"):
            continue
        data[key] = query_dict.get(key)

    received = (query_dict.get("vnp_SecureHash") or "").strip()
    if not received:
        txn_ref_early = str(query_dict.get("vnp_TxnRef") or "")
        oid_early = None
        if txn_ref_early.startswith("FS"):
            s2 = txn_ref_early[2:]
            if "_" in s2:
                s2 = s2.split("_")[0]
            if s2.isdigit():
                oid_early = int(s2)
        return False, {"reason": "missing_hash", "order_id": oid_early}

    sorted_keys = sorted(data.keys())
    sign_parts = []
    for k in sorted_keys:
        val = data[k]
        if val is None or val == "":
            continue
        sign_parts.append(f"{k}={_vnp_quote(str(val))}")
    sign_data = "&".join(sign_parts)
    expected = _hmac_sha512(secret, sign_data)
    txn_ref_early = str(data.get("vnp_TxnRef") or query_dict.get("vnp_TxnRef") or "")
    oid_early = None
    if txn_ref_early.startswith("FS"):
        s2 = txn_ref_early[2:]
        if "_" in s2:
            s2 = s2.split("_")[0]
        if s2.isdigit():
            oid_early = int(s2)
    if not hmac.compare_digest(expected.lower(), received.lower()):
        return False, {
            "reason": "bad_signature",
            "order_id": oid_early,
            "response_code": str(data.get("vnp_ResponseCode") or query_dict.get("vnp_ResponseCode") or ""),
        }

    txn_ref = str(data.get("vnp_TxnRef") or "")
    response_code = str(data.get("vnp_ResponseCode") or "")
    order_id = None
    if txn_ref.startswith("FS"):
        s2 = txn_ref[2:]
        if "_" in s2:
            s2 = s2.split("_")[0]
        if s2.isdigit():
            order_id = int(s2)

    ok = response_code == "00"
    return ok, {
        "order_id": order_id,
        "txn_ref": txn_ref,
        "response_code": response_code,
        "transaction_no": str(data.get("vnp_TransactionNo") or ""),
        "raw": data,
    }


def txn_ref_for_order(order_id: int) -> str:
    return f"FS{order_id}"


def query_dr(
    *,
    txn_ref: str,
    transaction_date: str,
    order_info: str = "truy van giao dich",
    ip_addr: str = "127.0.0.1",
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    API querydr — tra cứu giao dịch (POST JSON).
    transaction_date: yyyyMMddHHmmss — theo tài liệu thường là thời điểm giao dịch gốc (vd. vnp_PayDate khi đã có);
    nếu đơn vẫn pending có thể thử thời điểm tạo thanh toán (CreateDate) tùy cấu hình sandbox.
    """
    tmn = (getattr(settings, "VNP_TMN_CODE", None) or "").strip()
    secret = (getattr(settings, "VNP_HASH_SECRET", None) or "").strip()
    api_url = (getattr(settings, "VNP_API_URL", None) or "").strip() or (
        "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
    )
    if not tmn or not secret:
        raise ValueError("VNPay chưa cấu hình (VNP_TMN_CODE, VNP_HASH_SECRET).")

    rid = (request_id or uuid.uuid4().hex[:16]).strip()
    vnp_version = "2.1.0"
    command = "querydr"
    create_date = datetime.now(_VNP_TZ).strftime("%Y%m%d%H%M%S")
    safe_info = "".join(c for c in order_info if c.isalnum() or c in " -_.") or "truy van giao dich"

    hash_data = "|".join(
        [rid, vnp_version, command, tmn, txn_ref, transaction_date, create_date, ip_addr[:45], safe_info]
    )
    secure_hash = _hmac_sha512(secret, hash_data)

    payload = {
        "vnp_RequestId": rid,
        "vnp_TmnCode": tmn,
        "vnp_Command": command,
        "vnp_TxnRef": txn_ref,
        "vnp_OrderInfo": safe_info,
        "vnp_TransactionDate": transaction_date,
        "vnp_CreateDate": create_date,
        "vnp_IpAddr": ip_addr[:45],
        "vnp_Version": vnp_version,
        "vnp_SecureHash": secure_hash,
    }

    try:
        r = requests.post(api_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=30)
        r.raise_for_status()
        return json.loads(r.text)
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.exception("VNPay querydr failed: %s", e)
        raise ValueError("Không gọi được API tra cứu VNPay.") from e
