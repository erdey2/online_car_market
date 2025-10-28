from django.contrib.auth import get_user_model
from rest_framework.viewsets import ModelViewSet, ViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rolepermissions.roles import assign_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .serializers import UserRoleSerializer, ProfileSerializer, UserSerializer, UserRegistrationSerializer
from online_car_market.users.models import Profile
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin, IsSuperAdminOrAdmin
from rolepermissions.checkers import has_role
from rest_framework.decorators import action
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(tags=["Authentication & Users"]),
    retrieve=extend_schema(tags=["Authentication & Users"]),
    partial_update=extend_schema(tags=["Authentication & Users"]),
    me=extend_schema(tags=["Authentication & Users"]),
)
class ProfileViewSet(ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Profile.objects.all()
        return Profile.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        logger.info(f"Profile retrieved for {request.user.email}")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Profile updated for {request.user.email}")
        return Response(serializer.data)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    @extend_schema(
        summary="Get or update your own profile",
        responses=ProfileSerializer,
    )
    def me(self, request):
        profile = self.get_queryset().first()
        if not profile:
            return Response({"detail": "Profile not found."}, status=404)

        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(f"Profile (me) updated for {request.user.email}")
            return Response(serializer.data)

        return Response({"detail": "Method not allowed."}, status=405)

@extend_schema_view(
    create=extend_schema(
        tags=["Authentication & Users"],
        summary="Assign a role to a user",
        request=UserRoleSerializer,
        responses={200: UserRoleSerializer},
    )
)
class UserRoleViewSet(ViewSet):
    permission_classes = [IsSuperAdminOrAdmin]

    def create(self, request):
        serializer = UserRoleSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(
            f"Role assigned to {user.email}: {serializer.validated_data['role']}"
        )
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["Authentication & Users"],
        summary="List all buyers (user-level info)",
        responses={200: UserSerializer(many=True)},
    )
)
class BuyerUserViewSet(ReadOnlyModelViewSet):
    """ViewSet to list all buyers (user-level info)"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSuperAdminOrAdmin]
    http_method_names = ['get']

    def get_queryset(self):
        """Return all users with the 'buyer' role"""
        return [user for user in User.objects.all() if has_role(user, 'buyer')]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"{request.user.email} retrieved the list of buyers (user-level).")
        return Response(serializer.data)

