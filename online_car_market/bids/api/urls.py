from django.urls import path, include
from rest_framework.routers import DefaultRouter

from online_car_market.bids.api.views import BidViewSet, AuctionViewSet

router = DefaultRouter()

router.register(r'', BidViewSet, basename='bids')
router.register(r'', AuctionViewSet, basename='auctions')

urlpatterns = [
path('', include(router.urls)),
]
