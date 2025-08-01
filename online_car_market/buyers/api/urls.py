from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuyerViewSet, DealerProfileViewSet, RatingViewSet, LoyaltyProgramViewSet  # example view

router = DefaultRouter()
router.register(r'buyers', BuyerViewSet, basename='buyer')
router.register(r'dealers', DealerProfileViewSet, basename='dealer')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'loyalty', LoyaltyProgramViewSet, basename='loyalty')

urlpatterns = [
    path('', include(router.urls)),
]
