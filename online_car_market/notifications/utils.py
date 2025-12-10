from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification

def send_user_notification(recipient, message, data=None, save=True):
    """
    Create Notification (optional) and push to user's websocket group.
    :param recipient: User instance
    :param message: str
    :param data: dict optional structured payload
    :param save: if True, persist Notification to DB
    """
    payload = {
        "message": message,
        "data": data or {},
        "is_read": False,
    }

    if save:
        n = Notification.objects.create(recipient=recipient, message=message, data=data or {})
        payload.update({
            "id": n.id,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
        })

    channel_layer = get_channel_layer()
    group = f"user_{recipient.id}"
    async_to_sync(channel_layer.group_send)(
        group,
        {
            "type": "notify",         # maps to `notify` method in consumer
            "payload": payload,
        },
    )
    return payload

