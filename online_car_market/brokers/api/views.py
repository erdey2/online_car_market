from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from ..models import Broker, BrokerListing
from .serializers import BrokerSerializer, BrokerListingSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view


# Permission Classes
class CanManageBrokers(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.user == request.user

class CanManageBrokerListings(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.broker.user == request.user

# Broker ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Brokers - Profiles"]),
    retrieve=extend_schema(tags=["Brokers - Profiles"]),
    create=extend_schema(tags=["Brokers - Profiles"]),
    update=extend_schema(tags=["Brokers - Profiles"]),
    partial_update=extend_schema(tags=["Brokers - Profiles"]),
    destroy=extend_schema(tags=["Brokers - Profiles"]),
)
class BrokerViewSet(ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageBrokers()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'broker'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

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
