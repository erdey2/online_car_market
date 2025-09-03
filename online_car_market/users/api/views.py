from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import UserRoleSerializer, ProfileSerializer
from online_car_market.users.models import Profile
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin
from rolepermissions.checkers import has_role
import logging

logger = logging.getLogger(__name__)

@extend_schema(tags=["Profile Management"])
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


@extend_schema(tags=["Profile Management"])
class UserRoleViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    @extend_schema(
        request=UserRoleSerializer,
        responses={200: UserRoleSerializer}
    )
    def create(self, request):
        serializer = UserRoleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"Role assigned to {user.email}: {serializer.validated_data['role']}")
        return Response(serializer.data)

