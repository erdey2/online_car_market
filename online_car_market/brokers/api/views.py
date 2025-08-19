from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from ..models import Broker, BrokerListing
from .serializers import BrokerSerializer, BrokerListingSerializer, UpgradeToBrokerSerializer, VerifyBrokerSerializer
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin, IsBroker

class CanManageBrokerListings(BasePermission):
    def has_permission(self, request, view):
        # Example: only allow users with role 'broker' to access
        return request.user.is_authenticated and request.user.role == 'broker'

@extend_schema_view(
    list=extend_schema(tags=["Brokers - Profiles"], description="List all brokers (admin only)."),
    retrieve=extend_schema(tags=["Brokers - Profiles"], description="Retrieve a broker profile."),
    create=extend_schema(tags=["Brokers - Profiles"], description="Create a broker profile (admin only)."),
    update=extend_schema(tags=["Brokers - Profiles"], description="Update a broker profile (admin or owner)."),
    partial_update=extend_schema(tags=["Brokers - Profiles"], description="Partially update a broker profile."),
    destroy=extend_schema(tags=["Brokers - Profiles"], description="Delete a broker profile (admin only)."),
)
class BrokerViewSet(ModelViewSet):
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Broker.objects.all()
        return Broker.objects.filter(user=user)

    @extend_schema(
        tags=["Brokers - Profiles"],
        description="Verify a broker profile (admin/super_admin only).",
        responses=VerifyBrokerSerializer
    )
    @action(detail=True, methods=['patch'], serializer_class=VerifyBrokerSerializer)
    def verify(self, request, pk=None):
        broker = self.get_object()
        serializer = self.get_serializer(broker, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Brokers - Profiles"],
        description="Request to upgrade to broker role.",
        responses=BrokerSerializer
    )
    @action(detail=False, methods=['post'], serializer_class=UpgradeToBrokerSerializer)
    def upgrade(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        broker = serializer.save()
        return Response(BrokerSerializer(broker).data)

# BrokerListing ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Brokers - Listings"]),
    retrieve=extend_schema(tags=["Brokers - Listings"]),
    create=extend_schema(tags=["Brokers - Listings"]),
    update=extend_schema(tags=["Brokers - Listings"]),
    partial_update=extend_schema(tags=["Brokers - Listings"]),
    destroy=extend_schema(tags=["Brokers - Listings"]),
)
class BrokerListingViewSet(ModelViewSet):
    queryset = BrokerListing.objects.all()
    serializer_class = BrokerListingSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageBrokerListings()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'broker'):
            return self.queryset.filter(broker__user=user)
        return self.queryset.none()
