from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    BrokerProfileViewSet,
    BrokerRatingViewSet,
    BrokerVerificationViewSet,
    BrokerApplicationView,
    AdminBrokerViewSet,
)

router = routers.SimpleRouter()
router.register('profiles', BrokerProfileViewSet, basename='broker-profile')
router.register('verifications', BrokerVerificationViewSet, basename='broker-verifications')
router.register('ratings', BrokerRatingViewSet, basename='broker-ratings')

admin_router = routers.SimpleRouter()
admin_router.register('brokers', AdminBrokerViewSet, basename='admin-brokers')

urlpatterns = [
    path('', include(router.urls)),
    path('application/', BrokerApplicationView.as_view(), name='broker-application'),
    path('admin/', include(admin_router.urls)),
]
