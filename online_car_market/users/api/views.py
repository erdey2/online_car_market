from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from ..models import User
from .serializers import UserSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.response import Response


# Custom DRF Permission class for managing users
class CanManageUsers(BasePermission):
    """
    Allows access only to users with super_admin or admin role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_role(request.user, ['super_admin', 'admin'])

@extend_schema_view(
    list=extend_schema(tags=["users"]),
    retrieve=extend_schema(tags=["users"]),
    create=extend_schema(tags=["users"]),
    update=extend_schema(tags=["users"]),
    partial_update=extend_schema(tags=["users"]),
    destroy=extend_schema(tags=["users"]),
)
class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageUsers()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset.all()
        if user.is_authenticated:
            return self.queryset.filter(id=user.id)
        return self.queryset.none()

    @extend_schema(
        description="Retrieve the authenticated user's profile.",
        responses=UserSerializer
    )
    @action(detail=False, methods=["get"])
    def me(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

