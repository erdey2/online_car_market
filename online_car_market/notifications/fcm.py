import firebase_admin
from firebase_admin import messaging, credentials


cred = credentials.Certificate('/path/to/serviceAccountKey.json')
app = firebase_admin.initialize_app(cred)


def send_fcm_message(tokens, notification):
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=notification.verb, body=notification.description),
        data=notification.data or {},
        tokens=tokens
    )
    response = messaging.send_multicast(message)
    return response
