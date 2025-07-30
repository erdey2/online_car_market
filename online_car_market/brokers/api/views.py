from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Broker, BrokerListing
from .serializers import BrokerSerializer, BrokerListingSerializer
from online_car_market.users.api.views import IsAdmin
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(tags=["brokers"]),
    retrieve=extend_schema(tags=["brokers"]),
    create=extend_schema(tags=["brokers"]),
    update=extend_schema(tags=["brokers"]),
    destroy=extend_schema(tags=["brokers"]),
)
class BrokerViewSet(ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@extend_schema_view(
    list=extend_schema(tags=["brokers"]),
    retrieve=extend_schema(tags=["brokers"]),
    create=extend_schema(tags=["brokers"]),
    update=extend_schema(tags=["brokers"]),
    destroy=extend_schema(tags=["brokers"]),
)
class BrokerListingViewSet(ModelViewSet):
    queryset = BrokerListing.objects.all()
    serializer_class = BrokerListingSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
