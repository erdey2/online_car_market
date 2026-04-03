from django.apps import AppConfig
from .firebase import init_firebase

class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "online_car_market.notifications"

    def ready(self):
        import online_car_market.notifications.signals
        init_firebase()
