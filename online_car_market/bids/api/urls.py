from django.urls import path, include
from rest_framework.routers import DefaultRouter

from online_car_market.bids.api.views import BidViewSet, AuctionViewSet

router = DefaultRouter()

router.register(r'bids', BidViewSet, basename='bids')
router.register(r'auctions', AuctionViewSet, basename='auctions')

urlpatterns = [
path('', include(router.urls)),
]
