import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from online_car_market.notifications.routing import websocket_urlpatterns
from online_car_market.notifications.middleware import TokenAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

django_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": TokenAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})



