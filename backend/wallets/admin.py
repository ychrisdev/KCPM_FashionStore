from django.contrib import admin
from .models import Wallet, WalletTransaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at')

@admin.register(WalletTransaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'type', 'status', 'created_at')