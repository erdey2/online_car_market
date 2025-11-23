from celery import shared_task
from django.core.mail import send_mail
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, Device
from .fcm import send_fcm_message


@shared_task
def deliver_notification(notification_id, channels):
    n = Notification.objects.get(id=notification_id)
    payload = {
        'id': n.id,
        'verb': n.verb,
        'description': n.description,
        'data': n.data,
        'created_at': n.created_at.isoformat(),
    }

    # websocket
    if 'in_app' in channels:
        channel_layer = get_channel_layer()
        group_name = f'user_{n.recipient_id}'
        async_to_sync(channel_layer.group_send)(group_name, {
            'type':'notification.message',
            'notification': payload,
        })

    # push
    if 'push' in channels:
        devices = Device.objects.filter(user=n.recipient)
        tokens = [d.fcm_token for d in devices]
        if tokens:
            send_fcm_message(tokens, n)

    # email
    if 'email' in channels and n.recipient.email:
        send_mail(...)
