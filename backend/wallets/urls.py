from django.urls import path

from .views import (
    MyWalletView,
    WalletInfoView,
    WithdrawRequestView,
    WalletActionView,
    WalletDepositStartView,
    WalletDepositZalopaySyncView,
)

urlpatterns = [
    path("my-wallet/", MyWalletView.as_view(), name="wallet-my"),
    path("info/", WalletInfoView.as_view(), name="wallet-info"),
    path("withdraw/", WithdrawRequestView.as_view(), name="wallet-withdraw"),
    path("action/", WalletActionView.as_view(), name="wallet-action"),
    path("deposit/start/", WalletDepositStartView.as_view(), name="wallet-deposit-start"),
    path(
        "deposit/<int:pk>/zalopay-sync/",
        WalletDepositZalopaySyncView.as_view(),
        name="wallet-deposit-zalopay-sync",
    ),
]
