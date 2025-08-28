from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Broker, BrokerRating
from .serializers import BrokerSerializer, UpgradeToBrokerSerializer, VerifyBrokerSerializer, BrokerRatingSerializer
from online_car_market.users.permissions import IsSuperAdminOrAdminOrBuyer

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

@extend_schema(parameters=[OpenApiParameter(name="id", type=OpenApiTypes.INT, location="path", description="Broker ID")])
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

@extend_schema_view(
    list=extend_schema(tags=["Brokers - Ratings"], description="List all ratings for a broker."),
    retrieve=extend_schema(tags=["Brokers - Ratings"], description="Retrieve a specific broker rating."),
    create=extend_schema(tags=["Brokers - Ratings"], description="Create a broker rating (authenticated users only)."),
    update=extend_schema(tags=["Brokers - Ratings"], description="Update a broker rating (rating owner or admin only)."),
    partial_update=extend_schema(tags=["Brokers - Ratings"], description="Partially update a broker rating."),
    destroy=extend_schema(tags=["Brokers - Ratings"], description="Delete a broker rating (rating owner or admin only)."),
)
class BrokerRatingViewSet(ModelViewSet):
    serializer_class = BrokerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        broker_id = self.kwargs.get('broker_id')
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return BrokerRating.objects.filter(broker_id=broker_id)
        return BrokerRating.objects.filter(broker_id=broker_id, user=user)

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperAdminOrAdminOrBuyer()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        broker_id = self.kwargs.get('broker_pk')
        broker = Broker.objects.get(pk=broker_id)
        serializer.save(broker=broker, user=self.request.user)
