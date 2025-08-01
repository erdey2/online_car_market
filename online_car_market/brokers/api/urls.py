from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BrokerViewSet, BrokerListingViewSet  # example view

router = DefaultRouter()
router.register(r'brokers', BrokerViewSet, basename='broker')
router.register(r'brokers-listing', BrokerListingViewSet, basename='broker-listing')

urlpatterns = [
    path('', include(router.urls)),
]
