from rest_framework import serializers
from .models import WalletTransaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "transaction_id",
            "amount",
            "type",
            "status",
            "gateway",
            "gateway_ref",
            "created_at",
            "description",
        ]