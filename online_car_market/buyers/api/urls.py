from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuyerViewSet, LoyaltyProgramViewSet  # example view

router = DefaultRouter()
router.register(r'profiles', BuyerViewSet, basename='buyer')
# router.register(r'me', BuyerViewSet, basename='buyer')
router.register(r'loyalty', LoyaltyProgramViewSet, basename='loyalty')

urlpatterns = [
    path('', include(router.urls)),
]
