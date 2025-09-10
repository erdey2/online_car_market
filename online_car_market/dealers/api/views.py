from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from online_car_market.dealers.models import DealerProfile, DealerRating
from .serializers import DealerRatingSerializer, DealerProfileSerializer, VerifyDealerSerializer
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin
import logging

logger = logging.getLogger(__name__)

class DealerProfileViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileSerializer

    @extend_schema(
        tags=["Dealers - Profile"],
        description="Retrieve the authenticated user's DealerProfile information.",
        responses={200: DealerProfileSerializer}
    )
    def list(self, request):
        if not has_role(request.user, 'dealer'):
            return Response(
                {"detail": "User does not have dealer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            dealer_profile = DealerProfile.objects.get(profile__user=request.user)
            serializer = DealerProfileSerializer(dealer_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DealerProfile.DoesNotExist:
            return Response(
                {"detail": "Dealer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class IsRatingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or has_role(request.user, ['super_admin', 'admin'])

@extend_schema_view(
    list=extend_schema(tags=["Dealers - Ratings"], description="List all ratings for a dealer."),
    retrieve=extend_schema(tags=["Dealers - Ratings"], description="Retrieve a specific dealer rating."),
    create=extend_schema(tags=["Dealers - Ratings"], description="Create a dealer rating (authenticated users only)."),
    update=extend_schema(tags=["Dealers - Ratings"], description="Update a dealer rating (rating owner or admin only)."),
    partial_update=extend_schema(tags=["Dealers - Ratings"], description="Partially update a dealer rating."),
    destroy=extend_schema(tags=["Dealers - Ratings"], description="Delete a dealer rating (rating owner or admin only)."),
)
@extend_schema(
    parameters=[
        OpenApiParameter(name="dealer_pk", type=OpenApiTypes.INT, location="path", description="Parent Dealer ID"),
        OpenApiParameter(name="id", type=OpenApiTypes.INT, location="path", description="Rating ID"),
    ]
)
class DealerRatingViewSet(ModelViewSet):
    serializer_class = DealerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        dealer_pk = self.kwargs.get('dealer_pk')
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return DealerRating.objects.filter(dealer_id=dealer_pk)
        return DealerRating.objects.filter(dealer_id=dealer_pk, user=user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsRatingOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        dealer_pk = self.kwargs.get('dealer_pk')
        try:
            dealer = DealerProfile.objects.get(pk=dealer_pk)
            serializer.save(dealer=dealer, user=self.request.user)
            logger.info(f"Dealer rating created by {self.request.user.email} for dealer {dealer_pk}")
        except DealerProfile.DoesNotExist:
            logger.error(f"Dealer {dealer_pk} not found for rating creation")
            raise serializers.ValidationError({"dealer": "Dealer does not exist."})

@extend_schema_view(
    verify=extend_schema(
        tags=["Dealers - Verification"],
        request=VerifyDealerSerializer,
        responses={200: VerifyDealerSerializer},
        description="Verify a dealer profile (admin/super_admin only)."
    )
)
class DealerVerificationViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    @action(detail=True, methods=['patch'])
    def verify(self, request, pk=None):
        try:
            dealer = DealerProfile.objects.get(pk=pk)
            serializer = VerifyDealerSerializer(dealer, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(f"Dealer {dealer.pk} verification updated by {request.user.email}")
            return Response(serializer.data)
        except DealerProfile.DoesNotExist:
            logger.error(f"Dealer {pk} not found for verification")
            return Response({"error": "Dealer not found."}, status=404)
