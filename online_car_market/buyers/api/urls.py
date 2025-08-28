from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuyerViewSet, LoyaltyProgramViewSet  # example view

router = DefaultRouter()
router.register(r'buyers', BuyerViewSet, basename='buyer')
router.register(r'loyalty', LoyaltyProgramViewSet, basename='loyalty')

urlpatterns = [
    path('', include(router.urls)),
]
