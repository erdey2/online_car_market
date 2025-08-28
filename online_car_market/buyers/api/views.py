from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from ..models import Buyer, LoyaltyProgram
from .serializers import BuyerSerializer, LoyaltyProgramSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers

# PERMISSION CLASSES
class CanManageBuyers(BasePermission):
    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.user == request.user

class CanManageRatings(BasePermission):
    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.buyer == request.user

class CanManageLoyalty(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin'])

@extend_schema_view(
    list=extend_schema(tags=["Buyers - Profiles"], description="List all buyers (admin only)."),
    retrieve=extend_schema(tags=["Buyers - Profiles"], description="Retrieve a buyer profile."),
    create=extend_schema(tags=["Buyers - Profiles"], description="Create a buyer profile (admin only)."),
    update=extend_schema(tags=["Buyers - Profiles"], description="Update a buyer profile (admin or owner)."),
    partial_update=extend_schema(tags=["Buyers - Profiles"], description="Partially update a buyer profile."),
    destroy=extend_schema(tags=["Buyers - Profiles"], description="Delete a buyer profile (admin only)."),
)
class BuyerViewSet(ModelViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageBuyers()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'buyer'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

    def perform_create(self, serializer):
        # Expecting 'user' to be passed as an ID in the request
        user_id = self.request.data.get("user", {}).get("id") or self.request.data.get("user")

        if not user_id:
            raise serializers.ValidationError({"user": "User ID is required."})

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"user": "User not found."})

        serializer.save(user=user)

@extend_schema_view(
    list=extend_schema(tags=["Buyers - Loyalty"]),
    retrieve=extend_schema(tags=["Buyers - Loyalty"]),
    create=extend_schema(tags=["Buyers - Loyalty"]),
    update=extend_schema(tags=["Buyers - Loyalty"]),
    partial_update=extend_schema(tags=["Buyers - Loyalty"]),
    destroy=extend_schema(tags=["Buyers - Loyalty"]),
)
class LoyaltyProgramViewSet(ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageLoyalty()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'buyer'):
            return self.queryset.filter(buyer__user=user)
        return self.queryset.none()
