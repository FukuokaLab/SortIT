from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from sortIT.models import UserPreferences


@receiver(post_save, sender=User)
def create_user_sort_settings(sender, instance, created, **kwargs) -> None:
    if created:
        UserPreferences.objects.create(user=instance)
