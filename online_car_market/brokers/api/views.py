from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Broker, BrokerListing
from .serializers import BrokerSerializer, BrokerListingSerializer
from online_car_market.users.api.views import IsAdmin

class BrokerViewSet(ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

class BrokerListingViewSet(ModelViewSet):
    queryset = BrokerListing.objects.all()
    serializer_class = BrokerListingSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
