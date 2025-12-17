from rest_framework import serializers, status
from rest_framework.viewsets import (ModelViewSet, GenericViewSet,ViewSet)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from rolepermissions.checkers import has_role
from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse )

from .serializers import ( DealerRatingSerializer, DealerProfileSerializer, VerifyDealerSerializer, DealerStaffSerializer )
from ..models import DealerStaff
from online_car_market.dealers.models import DealerProfile, DealerRating

from online_car_market.users.permissions.drf_permissions import ( IsSuperAdmin, IsAdmin)
from online_car_market.users.permissions.business_permissions import ( IsRatingOwnerOrAdmin, IsDealerWithManageStaff)

import logging

logger = logging.getLogger(__name__)

class ProfileViewSet(GenericViewSet):
    """
    Retrieve or partially update the authenticated user's profile
    (dealer, seller, accountant, hr).
    """

    permission_classes = [IsAuthenticated]

    STAFF_ROLES = ["seller", "accountant", "hr"]

    def get_serializer_class(self):
        user = self.request.user

        if has_role(user, "dealer"):
            return DealerProfileSerializer

        if has_role(user, self.STAFF_ROLES):
            return DealerStaffSerializer

        # Required fallback to avoid schema errors
        return serializers.Serializer

    @extend_schema(
        tags=["Profiles"],
        responses={
            200: DealerProfileSerializer | DealerStaffSerializer,
            403: OpenApiResponse(description="User does not have an allowed role."),
            404: OpenApiResponse(description="Profile not found."),
        },
        description="Retrieve the authenticated user's profile.",
    )
    def retrieve(self, request, *args, **kwargs):
        user = request.user

        # Dealer profile
        if has_role(user, "dealer"):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
            except DealerProfile.DoesNotExist:
                return Response(
                    {"detail": "Dealer profile not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = DealerProfileSerializer(dealer_profile)
            return Response(serializer.data)

        # Staff profile (seller / accountant / hr)
        if has_role(user, self.STAFF_ROLES):
            staff_profile = (
                DealerStaff.objects.filter(user=user)
                .select_related("dealer", "user")
                .first()
            )

            if not staff_profile:
                return Response(
                    {"detail": "Staff profile not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = DealerStaffSerializer(staff_profile)
            return Response(serializer.data)

        return Response(
            {"detail": "User does not have an allowed role."},
            status=status.HTTP_403_FORBIDDEN,
        )

    @extend_schema(
        tags=["Profiles"],
        request=DealerProfileSerializer | DealerStaffSerializer,
        responses={
            200: DealerProfileSerializer | DealerStaffSerializer,
            403: OpenApiResponse(description="User does not have an allowed role."),
            404: OpenApiResponse(description="Profile not found."),
        },
        description="Partially update the authenticated user's profile.",
    )
    def partial_update(self, request, *args, **kwargs):
        user = request.user

        # Dealer update
        if has_role(user, "dealer"):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
            except DealerProfile.DoesNotExist:
                return Response(
                    {"detail": "Dealer profile not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = DealerProfileSerializer(
                dealer_profile, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        # Staff update
        if has_role(user, self.STAFF_ROLES):
            staff_profile = DealerStaff.objects.filter(user=user).first()
            if not staff_profile:
                return Response(
                    {"detail": "Staff profile not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = DealerStaffSerializer(
                staff_profile, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(
            {"detail": "User does not have an allowed role."},
            status=status.HTTP_403_FORBIDDEN,
        )

# DEALER STAFF MANAGEMENT
@extend_schema_view(
    create=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="Add a new staff member",
        request=DealerStaffSerializer,
        responses={201: DealerStaffSerializer},
    ),
    list=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="List all dealer staff",
        responses={200: DealerStaffSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="Retrieve staff details",
        responses={200: DealerStaffSerializer},
    ),
    update=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="Update staff information",
        request=DealerStaffSerializer,
        responses={200: DealerStaffSerializer},
    ),
    partial_update=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="Partially update staff information",
        request=DealerStaffSerializer,
        responses={200: DealerStaffSerializer},
    ),
    destroy=extend_schema(
        tags=["Dealers - Staff Management"],
        summary="Delete a staff member",
        responses={204: None},
    ),
)
class DealerStaffViewSet(ModelViewSet):
    queryset = DealerStaff.objects.all()
    serializer_class = DealerStaffSerializer
    permission_classes = [IsDealerWithManageStaff]

    def get_queryset(self):
        return self.queryset.filter(
            dealer=self.request.user.profile.dealer_profile
        )

# DEALER RATINGS
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Ratings"]),
    retrieve=extend_schema(tags=["Dealers - Ratings"]),
    create=extend_schema(tags=["Dealers - Ratings"]),
    update=extend_schema(tags=["Dealers - Ratings"]),
    partial_update=extend_schema(tags=["Dealers - Ratings"]),
    destroy=extend_schema(tags=["Dealers - Ratings"]),
)
@extend_schema(
    parameters=[
        OpenApiParameter(
            name="dealer_pk",
            type=OpenApiTypes.INT,
            location="path",
            description="Dealer ID",
        )
    ]
)
class DealerRatingViewSet(ModelViewSet):
    serializer_class = DealerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        dealer_pk = self.kwargs.get("dealer_pk")
        user = self.request.user

        if has_role(user, ["super_admin", "admin"]):
            return DealerRating.objects.filter(dealer_id=dealer_pk)

        return DealerRating.objects.filter(dealer_id=dealer_pk, user=user)

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsRatingOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        dealer_pk = self.kwargs.get("dealer_pk")
        try:
            dealer = DealerProfile.objects.get(pk=dealer_pk)
            serializer.save(dealer=dealer, user=self.request.user)
            logger.info(
                f"Dealer rating created by {self.request.user.email} for dealer {dealer_pk}"
            )
        except DealerProfile.DoesNotExist:
            logger.error(f"Dealer {dealer_pk} not found for rating creation")
            raise serializers.ValidationError(
                {"dealer": "Dealer does not exist."}
            )

# DEALER VERIFICATION
@extend_schema_view(
    verify=extend_schema(
        tags=["Dealers - Verification"],
        request=VerifyDealerSerializer,
        responses={200: VerifyDealerSerializer},
        description="Verify a dealer profile (admin/super_admin only).",
    )
)
class DealerVerificationViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        try:
            dealer = DealerProfile.objects.get(pk=pk)
            serializer = VerifyDealerSerializer(
                dealer,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            logger.info(
                f"Dealer {dealer.pk} verification updated by {request.user.email}"
            )
            return Response(serializer.data)

        except DealerProfile.DoesNotExist:
            logger.error(f"Dealer {pk} not found for verification")
            return Response(
                {"error": "Dealer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
