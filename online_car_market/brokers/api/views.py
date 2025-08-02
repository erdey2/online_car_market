from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from ..models import Broker, BrokerListing
from .serializers import BrokerSerializer, BrokerListingSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

@register_object_checker()
def has_manage_brokers_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin']) or (obj and obj.user == user)

@register_object_checker()
def has_manage_broker_listings_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin']) or (obj and obj.broker.user == user)

@extend_schema_view(
    list=extend_schema(tags=["brokers"]),
    retrieve=extend_schema(tags=["brokers"]),
    create=extend_schema(tags=["brokers"]),
    update=extend_schema(tags=["brokers"]),
    partial_update=extend_schema(tags=["brokers"]),
    destroy=extend_schema(tags=["brokers"]),
)
class BrokerViewSet(ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_brokers_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'broker'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

@extend_schema_view(
    list=extend_schema(tags=["brokers"]),
    retrieve=extend_schema(tags=["brokers"]),
    create=extend_schema(tags=["brokers"]),
    update=extend_schema(tags=["brokers"]),
    partial_update=extend_schema(tags=["brokers"]),
    destroy=extend_schema(tags=["brokers"]),
)
class BrokerListingViewSet(ModelViewSet):
    queryset = BrokerListing.objects.all()
    serializer_class = BrokerListingSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_broker_listings_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'broker'):
            return self.queryset.filter(broker__user=user)
        return self.queryset.none()
