from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageBuyers()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Buyer.objects.all()
        if has_role(user, 'buyer'):
            return Buyer.objects.filter(user=user)
        return Buyer.objects.none()

    def perform_create(self, serializer):
        """ Admins can create a buyer profile for any user by posting a user id. Buyers should not create again
        if they already have one.
        """
        user = self.request.user

        # If buyer tries to create, create only for themselves (and only if not exists)
        if has_role(user, 'buyer'):
            if Buyer.objects.filter(user=user).exists():
                raise serializers.ValidationError("You already have a buyer profile.")
            serializer.save(user=user)
            return

        # Admin path: allow creating for arbitrary user id
        user_id = self.request.data.get("user", {}).get("id") or self.request.data.get("user")
        if not user_id:
            raise serializers.ValidationError({"user": "User ID is required for admin creation."})

        from django.contrib.auth import get_user_model
        U = get_user_model()
        try:
            target_user = U.objects.get(id=user_id)
        except U.DoesNotExist:
            raise serializers.ValidationError({"user": "User not found."})
        if Buyer.objects.filter(user=target_user).exists():
            raise serializers.ValidationError("That user already has a buyer profile.")
        serializer.save(user=target_user)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """
        GET  /api/buyers/me/ -> return current buyer profile
        PATCH /api/buyers/me/ -> update current buyer profile (contact/address only)
        """
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "Only buyers have a profile."}, status=status.HTTP_403_FORBIDDEN)

        try:
            buyer = Buyer.objects.get(user=request.user)
        except Buyer.DoesNotExist:
            # Should be rare since we auto-create on registration; create a minimal one if missing
            buyer = Buyer.objects.create(user=request.user, contact='', address='')

        if request.method == 'GET':
            return Response(self.get_serializer(buyer).data)

        # PATCH
        serializer = self.get_serializer(buyer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

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
