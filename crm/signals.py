from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .access import AUTOSALON_BLOCKED_GROUP, AUTOSALON_HIDE_ATTORNEY_GROUP


@receiver(post_migrate)
def ensure_access_groups(sender, **kwargs):
    if sender.name != 'crm':
        return

    Group.objects.get_or_create(name=AUTOSALON_BLOCKED_GROUP)
    Group.objects.get_or_create(name=AUTOSALON_HIDE_ATTORNEY_GROUP)
