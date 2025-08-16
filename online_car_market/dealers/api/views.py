from rest_framework import serializers, status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.response import Response
from ..models import Dealer
from .serializers import DealerSerializer
from django.contrib.auth import get_user_model

# PERMISSION CLASSES
class CanManageDealers(BasePermission):
    """
    Allows access only to super_admin, admin, or the dealer themselves.
    """
    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.user == request.user

# VIEWSET
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Profiles"]),
    retrieve=extend_schema(tags=["Dealers - Profiles"]),
    create=extend_schema(tags=["Dealers - Profiles"]),
    update=extend_schema(tags=["Dealers - Profiles"]),
    partial_update=extend_schema(tags=["Dealers - Profiles"]),
    destroy=extend_schema(tags=["Dealers - Profiles"]),
)
class DealerProfileViewSet(ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer

    # Permissions
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageDealers()]
        return [IsAuthenticated()]

    # Queryset filtering
    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'dealer'):
            return self.queryset.filter(user=user)
        return self.queryset.none()

    # Create a dealer profile
    def perform_create(self, serializer):
        # Expecting 'user' to be passed as an ID in the request
        user_id = self.request.data.get("user", {}).get("id") or self.request.data.get("user")
        if not user_id:
            raise serializers.ValidationError({"user": "User ID is required."})

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"user": "User not found."})

        serializer.save(user=user)
