# online_car_market/dealers/api/urls.py

from django.urls import path, include
from rest_framework_nested import routers
from .views import (DealerRatingViewSet, DealerVerificationViewSet, ProfileViewSet,
                    DealerStaffViewSet, TopSellersViewSet, HighSalesRateCarsViewSet)

router = routers.SimpleRouter()
router.register(r'staff', DealerStaffViewSet, basename='dealer-staff')
router.register(r'ratings', DealerRatingViewSet, basename='dealer-rating')
router.register(r'verifications', DealerVerificationViewSet, basename='dealer-verification')
router.register(r'top-sellers', TopSellersViewSet, basename='top-sellers')
router.register(r'high-sale-cars', HighSalesRateCarsViewSet, basename='high-sales-rate-cars')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}), name='dealer-profile'),
]
