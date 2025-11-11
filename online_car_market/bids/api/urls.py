from django.urls import path, include
from rest_framework.routers import DefaultRouter

from online_car_market.bids.api.views import BidViewSet

router = DefaultRouter()

router.register(r'', BidViewSet, basename='bids')

urlpatterns = [
path('', include(router.urls)),
]
