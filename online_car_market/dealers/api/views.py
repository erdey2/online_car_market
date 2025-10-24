from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rolepermissions.checkers import has_role, has_permission, get_user_roles
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse
from online_car_market.dealers.models import DealerProfile, DealerRating
from .serializers import (DealerRatingSerializer, DealerProfileSerializer, VerifyDealerSerializer, DealerStaffSerializer)
from online_car_market.users.permissions import IsSuperAdmin, IsAdmin
from ..models import DealerStaff
import logging

logger = logging.getLogger(__name__)

class IsRatingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or has_role(request.user, ['super_admin', 'admin'])

class IsDealerWithManageStaff(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'dealer') and has_permission(request.user, 'manage_staff') and hasattr(request.user.profile, 'dealer_profile')

class ProfileViewSet(viewsets.ViewSet):
    """
    Endpoint to get or update the authenticated user's profile
    (dealer, seller, or accountant).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profiles"],
        description="Retrieve the authenticated user's profile (dealer, seller, accountant)."
    )
    def retrieve(self, request):
        user = request.user

        # Dealer
        if has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
            except DealerProfile.DoesNotExist:
                return Response({"detail": "Dealer profile not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DealerProfileSerializer(dealer_profile)
            return Response(serializer.data)

        # Seller / Accountant
        elif has_role(user, 'seller') or has_role(user, 'accountant'):
            staff_profile = DealerStaff.objects.filter(user=user).select_related('dealer', 'user').first()
            if not staff_profile:
                return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DealerStaffSerializer(staff_profile)
            return Response(serializer.data)

        return Response(
            {"detail": "User does not have a dealer, seller, or accountant role."},
            status=status.HTTP_403_FORBIDDEN
        )

    @extend_schema(
        tags=["Profiles"],
        description="Partially update the authenticated user's profile (dealer, seller, accountant)."
    )
    def partial_update(self, request):
        user = request.user

        # Dealer update
        if has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
            except DealerProfile.DoesNotExist:
                return Response({"detail": "Dealer profile not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DealerProfileSerializer(dealer_profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        # Seller / Accountant update
        elif has_role(user, 'seller') or has_role(user, 'accountant'):
            staff_profile = DealerStaff.objects.filter(user=user).first()
            if not staff_profile:
                return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DealerStaffSerializer(staff_profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(
            {"detail": "User does not have a dealer, seller, or accountant role."},
            status=status.HTTP_403_FORBIDDEN
        )


@extend_schema_view(
    create=extend_schema(
        tags=["Dealers - Staff Management"],
        description="Allow dealers to add sellers or accountants.",
        request=DealerStaffSerializer,
        responses={
            201: DealerStaffSerializer,
            403: OpenApiResponse(description="Permission denied")
        },
    ),
    list=extend_schema(
        tags=["Dealers - Staff Management"],
        description="List all staff members under the dealer.",
        responses={200: DealerStaffSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Dealers - Staff Management"],
        description="Retrieve staff by ID.",
        responses={
            200: DealerStaffSerializer,
            404: OpenApiResponse(description="Not found")
        },
    ),
    update=extend_schema(
        tags=["Dealers - Staff Management"],
        description="Update staff information (PUT).",
        request=DealerStaffSerializer,
        responses={200: DealerStaffSerializer, 403: "Permission denied"}
    ),
    partial_update=extend_schema(
        tags=["Dealers - Staff Management"],
        description="Partially update staff information (PATCH).",
        request=DealerStaffSerializer,
        responses={200: DealerStaffSerializer, 403: "Permission denied"}
    ),
    destroy=extend_schema(
        tags=["Dealers - Staff Management"],
        description="Delete a staff member (DELETE).",
        responses={204: None, 403: "Permission denied"}
    ),
)
class DealerStaffViewSet(viewsets.ModelViewSet):
    queryset = DealerStaff.objects.all()
    serializer_class = DealerStaffSerializer
    permission_classes = [IsDealerWithManageStaff]

    def get_queryset(self):
        return self.queryset.filter(dealer=self.request.user.profile.dealer_profile)

    def perform_create(self, serializer):
        serializer.save()

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
