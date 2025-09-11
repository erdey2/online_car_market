from django.urls import path, include
from rest_framework_nested import routers
from .views import DealerRatingViewSet, DealerVerificationViewSet, DealerProfileViewSet

router = routers.SimpleRouter()
# router.register(r'me', DealerProfileViewSet, basename='dealer-profile')
router.register(r'ratings', DealerRatingViewSet, basename='dealer-rating')
router.register(r'verifications', DealerVerificationViewSet, basename='dealer-verification')


urlpatterns = [
    path('', include(router.urls)),
    path('me/', DealerProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='broker-profile'),
]
