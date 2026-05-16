from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create profile when a new user is created (với phone/address mặc định)"""
    if kwargs.get('raw', False):
        return
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={"phone": "", "address": "", "role": "customer"}
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    if kwargs.get('raw', False):
        return
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.get_or_create(user=instance)
