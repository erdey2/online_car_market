from django.urls import path, include
from rest_framework_nested import routers
from .views import BrokerRatingViewSet, BrokerVerificationViewSet

router = routers.SimpleRouter()
router.register(r'ratings', BrokerRatingViewSet, basename='broker-rating')
router.register(r'verifications', BrokerVerificationViewSet, basename='broker-verification')

urlpatterns = [
    path('', include(router.urls)),
]
