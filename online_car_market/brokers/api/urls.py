from django.urls import path, include
from rest_framework_nested import routers
from .views import BrokerRatingViewSet, BrokerVerificationViewSet, BrokerProfileViewSet

router = routers.SimpleRouter()
# router.register(r'me', BrokerProfileViewSet, basename='broker-profile')
router.register(r'ratings', BrokerRatingViewSet, basename='broker-rating')
router.register(r'verifications', BrokerVerificationViewSet, basename='broker-verification')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', BrokerProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='broker-profile'),
]
