from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.viewsets import (ModelViewSet, ViewSet, ReadOnlyModelViewSet)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from rolepermissions.checkers import has_role
from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiResponse, inline_serializer)

from .serializers import ( DealerRatingSerializer, DealerProfileSerializer, VerifyDealerSerializer, DealerStaffSerializer )
from ..models import DealerStaff
from online_car_market.dealers.models import DealerProfile, DealerRating

from online_car_market.users.permissions.drf_permissions import IsSuperAdmin
from online_car_market.users.permissions.business_permissions import ( IsRatingOwnerOrAdmin, IsDealerWithManageStaff)
from ..services import approve_dealer, reactivate_dealer, suspend_dealer, reject_dealer

import logging

logger = logging.getLogger(__name__)

class DealerApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Dealers"],
        summary="Apply or re-apply as dealer",
        description="""
                Submit a dealer application.

                Rules:
                - First-time users can apply
                - Re-application allowed ONLY if previously REJECTED
                - Blocks duplicate applications if status is:
                  PENDING, APPROVED, or SUSPENDED
                """,
        request=inline_serializer(
            name="DealerApplicationRequest",
            fields={
                "company_name": serializers.CharField(),
                "license_number": serializers.CharField(),
                "tax_id": serializers.CharField(),
                "telebirr_account": serializers.CharField(required=False),
            },
        ),
        responses={
            201: OpenApiResponse(description="Dealer application submitted"),
            200: OpenApiResponse(description="Dealer application re-submitted"),
            400: OpenApiResponse(description="Application already exists or invalid"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def post(self, request):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response({"detail": "Profile not found."}, status=400)

        existing = DealerProfile.objects.filter(
            profile=profile
        ).first()

        if existing:
            if existing.status in [
                DealerProfile.Status.PENDING,
                DealerProfile.Status.APPROVED,
                DealerProfile.Status.SUSPENDED,
            ]:
                return Response(
                    {"detail": f"Application already exists with status '{existing.status}'."},
                    status=400,
                )

            # Re-apply if rejected
            if existing.status == DealerProfile.Status.REJECTED:
                existing.status = DealerProfile.Status.PENDING
                existing.reviewed_by = None
                existing.reviewed_at = None
                existing.rejection_reason = None
                existing.save()
                return Response({"detail": "Dealer application re-submitted."})

        DealerProfile.objects.create(
            profile=profile,
            company_name=request.data.get("company_name"),
            license_number=request.data.get("license_number"),
            tax_id=request.data.get("tax_id"),
            telebirr_account=request.data.get("telebirr_account"),
        )

        return Response({"detail": "Dealer application submitted."}, status=201)

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Dealer Management"],
        summary="List dealer applications",
        description="""
        List dealer applications for admin review.

        Query params:
        - status: PENDING | APPROVED | REJECTED | SUSPENDED
        """
    ),
    retrieve=extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Retrieve dealer application details",
    ),
)
class AdminDealerViewSet(ReadOnlyModelViewSet):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        queryset = DealerProfile.objects.select_related("profile", "profile__user")

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by("-created_at")

    @extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Approve dealer application",
        responses={200: OpenApiResponse(description="Dealer approved successfully")},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        dealer = self.get_object()
        approve_dealer(dealer, request.user)
        return Response({"detail": "Dealer approved."})

    @extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Reject dealer application",
        request=inline_serializer(
            name="RejectDealerRequest",
            fields={
                "rejection_reason": serializers.CharField(),
            },
        ),
        responses={200: OpenApiResponse(description="Dealer rejected successfully")},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        dealer = self.get_object()
        reason = request.data.get("rejection_reason")

        if not reason:
            return Response({"detail": "rejection_reason required"}, status=400)

        reject_dealer(dealer, request.user, reason)
        return Response({"detail": "Dealer rejected."})

    @extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Suspend dealer",
        responses={200: OpenApiResponse(description="Dealer suspended successfully")},
    )
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        dealer = self.get_object()
        suspend_dealer(dealer, request.user)
        return Response({"detail": "Dealer suspended."})

    @extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Reactivate dealer",
        responses={200: OpenApiResponse(description="Dealer reactivated successfully")},
    )
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        dealer = self.get_object()
        reactivate_dealer(dealer, request.user)
        return Response({"detail": "Dealer reactivated."})

    @extend_schema(
        tags=["Admin - Dealer Management"],
        summary="Verify dealer",
        description="Allows Super Admin to update dealer verification status and notes.",
        request=VerifyDealerSerializer,
        responses={200: DealerProfileSerializer},
    )
    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        dealer = self.get_object()

        serializer = VerifyDealerSerializer(
            dealer,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

@extend_schema_view(
    me=extend_schema(
        tags=["Dealers"],
        summary="Get my profile",
    ),
    update_me=extend_schema(
        tags=["Dealers"],
        summary="Update my profile",
    ),
)
class ProfileViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    STAFF_ROLES = ["seller", "accountant", "hr"]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        user = request.user

        # Dealer
        if has_role(user, "dealer"):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
            except DealerProfile.DoesNotExist:
                return Response({"detail": "Dealer profile not found."}, status=404)

            return Response(DealerProfileSerializer(dealer_profile).data)

        # Staff
        if has_role(user, self.STAFF_ROLES):
            staff_profile = DealerStaff.objects.filter(user=user).first()
            if not staff_profile:
                return Response({"detail": "Staff profile not found."}, status=404)

            return Response(DealerStaffSerializer(staff_profile).data)

        return Response({"detail": "Not allowed."}, status=403)

    @action(detail=False, methods=["patch"], url_path="me")
    def update_me(self, request):
        user = request.user

        if not has_role(user, "dealer"):
            return Response({"detail": "Only dealers can update profile."}, status=403)

        try:
            dealer_profile = DealerProfile.objects.get(profile__user=user)
        except DealerProfile.DoesNotExist:
            return Response({"detail": "Dealer profile not found."}, status=404)

        serializer = DealerProfileSerializer(
            dealer_profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

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
    serializer_class = DealerStaffSerializer
    permission_classes = [IsDealerWithManageStaff]

    def get_queryset(self):
        profile = getattr(self.request.user, "profile", None)
        if not profile or not hasattr(profile, "dealer_profile"):
            return DealerStaff.objects.none()

        return DealerStaff.objects.filter(
            dealer=profile.dealer_profile
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
class DealerRatingViewSet(ModelViewSet):
    serializer_class = DealerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        dealer_id = self.request.query_params.get("dealer")

        queryset = DealerRating.objects.all()

        if dealer_id:
            queryset = queryset.filter(dealer_id=dealer_id)

        if has_role(user, "super_admin") or has_role(user, "admin"):
            return queryset

        return queryset.filter(user=user)

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsRatingOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        dealer_id = self.request.data.get("dealer")

        if not dealer_id:
            raise serializers.ValidationError({"dealer": "Dealer ID is required."})

        try:
            dealer = DealerProfile.objects.get(pk=dealer_id)
        except DealerProfile.DoesNotExist:
            raise serializers.ValidationError({"dealer": "Dealer does not exist."})

        serializer.save(dealer=dealer, user=self.request.user)

        logger.info(
            f"Dealer rating created by {self.request.user.email} for dealer {dealer_id}"
        )

