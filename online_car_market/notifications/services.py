from .models import Notification


def notify_user(user, message, data=None):
    return Notification.objects.create(
        recipient=user,
        message=message,
        data=data or {},
    )
