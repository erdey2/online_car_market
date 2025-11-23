from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, DeviceViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notifications')
router.register(r'devices', DeviceViewSet, basename='devices')

urlpatterns = [
    path('', include(router.urls)),
]
