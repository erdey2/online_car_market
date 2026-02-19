import logging
from django.contrib.auth import get_user_model
from rest_framework.viewsets import ModelViewSet, ViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import UserRoleSerializer, ProfileSerializer, UserSerializer, ERPLoginSerializer, AdminLoginSerializer
from online_car_market.users.permissions.drf_permissions import IsSuperAdminOrAdmin
from rest_framework.decorators import action
from dj_rest_auth.views import LoginView
from ..services.profile_service import ProfileService
from ..services.user_service import UserService

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
        return ProfileService.get_visible_profiles(self.request.user)

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
        return Response(serializer.data)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    @extend_schema(
        summary="Get or update your own profile",
        responses=ProfileSerializer,
    )
    def me(self, request):
        profile = ProfileService.get_my_profile(request.user)
        if not profile:
            return Response({"detail": "Profile not found."}, status=404)

        if request.method == "GET":
            return Response(self.get_serializer(profile).data)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_profile = ProfileService.update_profile(
            profile, serializer.validated_data
        )

        logger.info(f"Profile (me) updated for {request.user.email}")
        return Response(self.get_serializer(updated_profile).data)

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
        return UserService.get_buyers()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"{request.user.email} retrieved the list of buyers (user-level).")
        return Response(serializer.data)

class ERPLoginView(LoginView):
    serializer_class = ERPLoginSerializer

class AdminLoginView(LoginView):
    serializer_class = AdminLoginSerializer



