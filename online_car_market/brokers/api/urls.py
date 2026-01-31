from django.urls import path, include
from rest_framework_nested import routers
from .views import (BrokerProfileViewSet, BrokerRatingViewSet, BrokerVerificationViewSet,
                    BrokerApplicationView, AdminBrokerActionView)

# Main broker router
router = routers.SimpleRouter()
router.register('profiles', BrokerProfileViewSet, basename='broker-profile')
router.register(r'verifications', BrokerVerificationViewSet, basename='broker-verifications')
router.register(r'ratings', BrokerRatingViewSet, basename='broker-ratings')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Broker self-application
    path('application/', BrokerApplicationView.as_view(), name='broker-application'),
    # Admin workflow actions (lookup by User ID)
    path('admin/<int:id>/<str:action>/', AdminBrokerActionView.as_view(), name='admin-broker-action'),
]
