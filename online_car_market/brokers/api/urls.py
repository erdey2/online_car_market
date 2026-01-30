from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    BrokerProfileViewSet,
    BrokerRatingViewSet,
    BrokerVerificationViewSet,
    BrokerApplicationView,
    AdminBrokerActionView
)

# Main broker router
router = routers.SimpleRouter()
router.register('profiles', BrokerProfileViewSet, basename='broker-profile')

# Nested routes under broker profiles
profiles_router = routers.NestedSimpleRouter(router, r'profiles', lookup='broker')
profiles_router.register(r'ratings', BrokerRatingViewSet, basename='broker-ratings')
profiles_router.register(r'verifications', BrokerVerificationViewSet, basename='broker-verifications')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    path('', include(profiles_router.urls)),

    # Broker self-application
    path('application/', BrokerApplicationView.as_view(), name='broker-application'),

    # Admin workflow actions (lookup by User ID now)
    path(
        'admin/<int:id>/<str:action>/',
        AdminBrokerActionView.as_view(),
        name='admin-broker-action'
    ),
]
