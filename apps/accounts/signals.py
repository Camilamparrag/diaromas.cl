"""Señales de la app de cuentas."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def crear_perfil(sender, instance, created, **kwargs):
    """Crea (o completa) el perfil asociado al usuario."""
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)