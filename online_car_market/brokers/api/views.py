from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from online_car_market.brokers.models import BrokerProfile, BrokerRating
from .serializers import VerifyBrokerSerializer, BrokerProfileSerializer, BrokerRatingSerializer
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin

import logging

logger = logging.getLogger(__name__)

class IsRatingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or has_role(request.user, ['super_admin', 'admin'])

class BrokerProfileViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    """
    A singleton-style endpoint for the authenticated broker's profile.
    Only supports GET (retrieve) and PATCH (update).
    """
    serializer_class = BrokerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            broker_profile = BrokerProfile.objects.get(profile__user=self.request.user)
        except BrokerProfile.DoesNotExist:
            raise NotFound(detail="Broker profile not found.")

        if not has_role(self.request.user, 'broker'):
            raise PermissionDenied(detail="User does not have broker role.")

        return broker_profile

    @extend_schema(
        tags=["Brokers - Profile"],
        description="Retrieve the authenticated broker's profile."
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        tags=["Brokers - Profile"],
        description="Partially update the authenticated broker's profile."
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(tags=["Brokers - Ratings"], description="List all ratings for a broker."),
    retrieve=extend_schema(tags=["Brokers - Ratings"], description="Retrieve a specific broker rating."),
    create=extend_schema(tags=["Brokers - Ratings"], description="Create a broker rating (authenticated users only)."),
    update=extend_schema(tags=["Brokers - Ratings"], description="Update a broker rating (rating owner or admin only)."),
    partial_update=extend_schema(tags=["Brokers - Ratings"], description="Partially update a broker rating."),
    destroy=extend_schema(tags=["Brokers - Ratings"], description="Delete a broker rating (rating owner or admin only)."),
)
@extend_schema(
    parameters=[
        OpenApiParameter(name="broker_pk", type=OpenApiTypes.INT, location="path", description="Parent Broker ID"),
        OpenApiParameter(name="id", type=OpenApiTypes.INT, location="path", description="Rating ID"),
    ]
)
class BrokerRatingViewSet(ModelViewSet):
    serializer_class = BrokerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        broker_pk = self.kwargs.get('broker_pk')
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return BrokerRating.objects.filter(broker_id=broker_pk)
        return BrokerRating.objects.filter(broker_id=broker_pk, user=user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsRatingOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        broker_pk = self.kwargs.get('broker_pk')
        try:
            broker = BrokerProfile.objects.get(pk=broker_pk)
            serializer.save(broker=broker, user=self.request.user)
            logger.info(f"Broker rating created by {self.request.user.email} for broker {broker_pk}")
        except BrokerProfile.DoesNotExist:
            logger.error(f"Broker {broker_pk} not found for rating creation")
            raise serializers.ValidationError({"broker": "Broker does not exist."})

@extend_schema_view(
    verify=extend_schema(
        tags=["Brokers - Verification"],
        request=VerifyBrokerSerializer,
        responses={200: VerifyBrokerSerializer},
        description="Verify a broker profile (admin/super_admin only)."
    )
)
class BrokerVerificationViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    @action(detail=True, methods=['patch'])
    def verify(self, request, pk=None):
        try:
            broker = BrokerProfile.objects.get(pk=pk)
            serializer = VerifyBrokerSerializer(broker, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(f"Broker {broker.pk} verification updated by {request.user.email}")
            return Response(serializer.data)
        except BrokerProfile.DoesNotExist:
            logger.error(f"Broker {pk} not found for verification")
            return Response({"error": "Broker not found."}, status=404)
