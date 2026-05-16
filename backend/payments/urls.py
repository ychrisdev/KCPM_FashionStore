from django.urls import path

from .views import MomoNotifyView, MomoReturnView, VnpayIpnView, VnpayReturnView, ZalopayCallbackView

urlpatterns = [
    path("vnpay/return/", VnpayReturnView.as_view(), name="vnpay_return"),
    path("vnpay/ipn/", VnpayIpnView.as_view(), name="vnpay_ipn"),
    path("momo/return/", MomoReturnView.as_view(), name="momo_return"),
    path("momo/notify/", MomoNotifyView.as_view(), name="momo_notify"),
    path("zalopay/callback/", ZalopayCallbackView.as_view(), name="zalopay_callback"),
]
