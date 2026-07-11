# core/validators.py
import re
from rest_framework import serializers

PHONE_REGEX = r'^0(3|5|7|8|9)[0-9]{8}$'
PHONE_PATTERN = re.compile(PHONE_REGEX)

def validate_phone_format(value: str) -> str:
    """
    Dùng chung cho mọi serializer cần validate SĐT VN.
    Ném ValidationError nếu sai định dạng.
    """
    if value and not PHONE_PATTERN.match(value):
        raise serializers.ValidationError("Số điện thoại không đúng định dạng")
    return value