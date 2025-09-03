from django.urls import path, include
from rest_framework_nested import routers
from .views import DealerRatingViewSet, DealerVerificationViewSet

router = routers.SimpleRouter()
router.register(r'ratings', DealerRatingViewSet, basename='dealer-rating')
router.register(r'verifications', DealerVerificationViewSet, basename='dealer-verification')

urlpatterns = [
    path('', include(router.urls)),
]
