from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from ..models import Buyer, Dealer, Rating, LoyaltyProgram
from .serializers import BuyerSerializer, DealerSerializer, RatingSerializer, LoyaltyProgramSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

@register_object_checker()
def has_manage_buyers_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin']) or (obj and obj.user == user)

@register_object_checker()
def has_manage_dealers_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin']) or (obj and obj.user == user)

@register_object_checker()
def has_manage_ratings_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin']) or (obj and obj.buyer == user)

@register_object_checker()
def has_manage_loyalty_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin'])

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    partial_update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class BuyerViewSet(ModelViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_buyers_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'buyer'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

@extend_schema_view(
    list=extend_schema(tags=["dealers"]),
    retrieve=extend_schema(tags=["dealers"]),
    create=extend_schema(tags=["dealers"]),
    update=extend_schema(tags=["dealers"]),
    partial_update=extend_schema(tags=["dealers"]),
    destroy=extend_schema(tags=["dealers"]),
)
class DealerProfileViewSet(ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_dealers_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'dealer'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    partial_update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class RatingViewSet(ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_ratings_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'buyer'):
            return self.queryset.filter(buyer=user)
        return self.queryset.none()

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    partial_update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class LoyaltyProgramViewSet(ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_loyalty_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'buyer'):
            return self.queryset.filter(buyer__user=user)
        return self.queryset.none()
