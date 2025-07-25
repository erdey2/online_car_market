from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from online_car_market.brokers.models import Broker, BrokerListing
from online_car_market.brokers.api.serializers import BrokerSerializer, BrokerListingSerializer
from online_car_market.users.api.views import IsAdmin

class BrokerViewSet(ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

class BrokerListingViewSet(ModelViewSet):
    queryset = BrokerListing.objects.all()
    serializer_class = BrokerListingSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
