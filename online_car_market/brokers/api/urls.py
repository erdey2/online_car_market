from django.urls import path, include
from rest_framework_nested import routers
from .views import BrokerRatingViewSet, BrokerVerificationViewSet, BrokerProfileViewSet

router = routers.SimpleRouter()
router.register(r'ratings', BrokerRatingViewSet, basename='broker-rating')
router.register(r'verifications', BrokerVerificationViewSet, basename='broker-verification')
router.register(r'brokers/me', BrokerProfileViewSet, basename='broker-profile')

urlpatterns = [
    path('', include(router.urls)),
]
