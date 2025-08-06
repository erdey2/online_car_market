from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from ..models import Dealer
from .serializers import DealerSerializer

# -----------------------
# PERMISSION CLASSES
# -----------------------

class CanManageDealers(BasePermission):
    def has_object_permission(self, request, view, obj):
        return has_role(request.user, ['super_admin', 'admin']) or obj.user == request.user

# -----------------------
# VIEWSETS
# -----------------------

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

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageDealers()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if has_role(user, 'dealer'):
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
