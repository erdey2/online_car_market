from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from .views import BrokerViewSet, BrokerRatingViewSet

router = DefaultRouter()
router.register(r'profiles', BrokerViewSet, basename='broker')

brokers_router = NestedSimpleRouter(router, r'profiles', lookup='broker')
brokers_router.register(r'ratings', BrokerRatingViewSet, basename='broker-rating')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(brokers_router.urls)),
]
