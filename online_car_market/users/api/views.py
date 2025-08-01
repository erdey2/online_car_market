from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import BasePermission
from online_car_market.users.models import User
from .serializers import UserSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    list=extend_schema(tags=["users"]),
    retrieve=extend_schema(tags=["users"]),
    update=extend_schema(tags=["users"]),
)
class UserViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user and user.is_authenticated:
            return self.queryset.filter(id=user.id)
        return self.queryset.none()

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role == 'super_admin'

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role in ['super_admin', 'admin']

class IsSales(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role in ['super_admin', 'admin', 'sales']

class IsAccounting(BasePermission):
    def has_permission(self, request, view):
        return request.user.userprofile.role in ['super_admin', 'admin', 'accounting']
