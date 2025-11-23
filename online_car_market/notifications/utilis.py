from .models import Notification
from .tasks import deliver_notification

def create_notification(recipient, actor=None, verb='', description='', data=None, channels=None):
    data = data or {}
    n = Notification.objects.create(recipient=recipient, actor=actor, verb=verb, description=description, data=data )
    # enqueue deliver job for background processing
    deliver_notification.delay(n.id, channels or ['in_app','push','email'])
    return n
