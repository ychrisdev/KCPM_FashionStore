from rest_framework import serializers

from .models import Contact, Feedback, Policy


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ("id", "name", "email", "phone", "subject", "message", "handled", "created_at")
        read_only_fields = ("created_at",)

    def create(self, validated_data):
        validated_data.pop("handled", None)
        return super().create(validated_data)


class FeedbackSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Feedback
        fields = ("id", "user", "username", "message", "handled", "created_at")
        read_only_fields = ("user", "username", "created_at")

    def create(self, validated_data):
        validated_data.pop("handled", None)
        return super().create(validated_data)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ("id", "title", "content")
