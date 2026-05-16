from django.contrib import admin
from .models import Contact, Feedback, Policy


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'subject', 'created_at')
    search_fields = ('name', 'email', 'phone', 'subject', 'message')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    search_fields = ('message',)


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title', 'content')
