from django.db.models.signals import post_save
from django.dispatch import receiver
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model
from .models import Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

User = get_user_model()

@receiver(post_save, sender=Car)
def notify_new_car(sender, instance, created, **kwargs):
    if not created:
        return

    admin_users = User.objects.filter(is_superuser=True)

    for user in admin_users:
        n = Notification.objects.create(recipient=user, verb="new_car", message=f"A new car '{instance.title}' has been posted." )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "send_notification",
                "data": {
                    "id": n.id,
                    "message": n.message,
                    "verb": n.verb,
                    "created_at": str(n.created_at)
                }
            }
        )
