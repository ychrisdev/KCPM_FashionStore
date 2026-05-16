from django.contrib import admin
from .models import BirthdayEmailTemplate, Profile


@admin.register(BirthdayEmailTemplate)
class BirthdayEmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "email_subject", "discount_code")

    def has_add_permission(self, request):
        return not BirthdayEmailTemplate.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'phone',
        'address',
        'birth_date',
        'birthday_reminder_sent_for_year',
    )
    search_fields = ('user__username', 'user__email', 'phone')
