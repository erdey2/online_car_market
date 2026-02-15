from online_car_market.brokers.services import approve_broker, reject_broker, suspend_broker, reactivate_broker
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.decorators import action

from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiTypes, OpenApiResponse,
                                   inline_serializer, OpenApiParameter)

from rolepermissions.checkers import has_role

from online_car_market.brokers.models import BrokerProfile, BrokerRating
from online_car_market.brokers.api.serializers import BrokerProfileSerializer, BrokerRatingSerializer, VerifyBrokerSerializer
from online_car_market.users.permissions.drf_permissions import IsAdmin, IsSuperAdmin
from online_car_market.users.permissions.business_permissions import IsRatingOwnerOrAdmin

logger = logging.getLogger(__name__)

# Broker Application
class BrokerApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Brokers"],
        summary="Apply or re-apply as broker",
        description="""
            Submit a broker application.

            Rules:
            - First-time users can apply
            - Re-application allowed ONLY if previously REJECTED
            - Blocks duplicate applications if status is:
              PENDING, APPROVED, or SUSPENDED
            """,
        request=inline_serializer(
            name="BrokerApplicationRequest",
            fields={
                "national_id": serializers.CharField(),
                "telebirr_account": serializers.CharField(required=False),
            },
        ),
        responses={
            201: OpenApiResponse(description="Broker application submitted"),
            200: OpenApiResponse(description="Broker application re-submitted"),
            400: OpenApiResponse(description="Application already exists or invalid"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def post(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return Response(
                {"detail": "User profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Block if an active or in-review application exists
        existing = BrokerProfile.objects.filter(
            profile=profile,
            status__in=[
                BrokerProfile.Status.PENDING,
                BrokerProfile.Status.APPROVED,
                BrokerProfile.Status.SUSPENDED,
            ],
        ).first()

        if existing:
            return Response(
                {
                    "detail": f"Broker application already exists with status '{existing.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Allow re-application ONLY if previously rejected
        rejected = BrokerProfile.objects.filter(
            profile=profile,
            status=BrokerProfile.Status.REJECTED,
        ).first()

        if rejected:
            rejected.national_id = request.data.get("national_id")
            rejected.telebirr_account = request.data.get("telebirr_account", rejected.telebirr_account)
            rejected.status = BrokerProfile.Status.PENDING
            rejected.reviewed_at = None
            rejected.reviewed_by = None
            rejected.rejection_reason = None
            rejected.save(update_fields=[
                "national_id",
                "telebirr_account",
                "status",
                "updated_at",
                "reviewed_at",
                "reviewed_by",
                "rejection_reason",
            ])

            return Response(
                {"detail": "Broker application re-submitted. Await admin approval."},
                status=status.HTTP_200_OK,
            )

        # First-time application
        BrokerProfile.objects.create(
            profile=profile,
            national_id=request.data.get("national_id"),
            telebirr_account=request.data.get("telebirr_account", ""),
            status=BrokerProfile.Status.PENDING,
        )

        return Response(
            {"detail": "Broker application submitted. Await admin approval."},
            status=status.HTTP_201_CREATED,
        )

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Broker Management"],
        summary="List broker applications",
        description="""
        List broker applications for admin review.

        Query params:
        - status: PENDING | APPROVED | REJECTED | SUSPENDED
        """
    ),
    retrieve=extend_schema(
        tags=["Admin - Broker Management"],
        summary="Retrieve broker application details",
    ),
)
class AdminBrokerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrokerProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsSuperAdmin]

    def get_queryset(self):
        queryset = BrokerProfile.objects.select_related(
            "profile", "profile__user"
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by("-created_at")

    # Admin Actions
    @extend_schema(
        tags=["Admin - Broker Management"],
        summary="Approve broker application",
        responses={200: OpenApiResponse(description="Broker approved successfully")},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        broker = self.get_object()
        approve_broker(broker, request.user)

        logger.info(f"Admin {request.user.email} approved broker {broker.pk}")
        return Response(
            {"detail": "Broker approved successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin - Broker Management"],
        summary="Reject broker application",
        request=inline_serializer(
            name="RejectBrokerRequest",
            fields={
                "rejection_reason": serializers.CharField(),
            },
        ),
        responses={200: OpenApiResponse(description="Broker rejected successfully")},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        broker = self.get_object()

        reason = request.data.get("rejection_reason")
        if not reason:
            return Response(
                {"detail": "rejection_reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reject_broker(broker, request.user, reason)

        logger.info(f"Admin {request.user.email} rejected broker {broker.pk}")
        return Response(
            {"detail": "Broker rejected successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin - Broker Management"],
        summary="Suspend broker",
        responses={200: OpenApiResponse(description="Broker suspended successfully")},
    )
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        broker = self.get_object()
        suspend_broker(broker, request.user)

        logger.info(f"Admin {request.user.email} suspended broker {broker.pk}")
        return Response(
            {"detail": "Broker suspended successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin - Broker Management"],
        summary="Reactivate broker",
        responses={200: OpenApiResponse(description="Broker reactivated successfully")},
    )
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        broker = self.get_object()
        reactivate_broker(broker, request.user)

        logger.info(f"Admin {request.user.email} reactivated broker {broker.pk}")
        return Response(
            {"detail": "Broker reactivated successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin - Broker Management"],
        summary="Verify broker profile",
        description="Verify an approved broker profile (Admin/Super Admin only).",
        request=VerifyBrokerSerializer,
        responses={
            200: VerifyBrokerSerializer,
            400: OpenApiResponse(description="Only approved brokers can be verified."),
            404: OpenApiResponse(description="Broker not found."),
        },
    )
    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        broker = self.get_object()

        if broker.status != BrokerProfile.Status.APPROVED:
            return Response(
                {"detail": "Only approved brokers can be verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VerifyBrokerSerializer(
            broker,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            f"Admin {request.user.email} verified broker {broker.pk}"
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


# Broker Profile ViewSet
@extend_schema_view(
    me=extend_schema(
        tags=["Brokers"],
        summary="Get my profile",
        description="Returns the authenticated broker's own profile.",
    ),
    update_me=extend_schema(
        tags=["Brokers"],
        summary="Update my profile",
        description="Partially update the authenticated broker's profile.",
    ),
)
class BrokerProfileViewSet(viewsets.GenericViewSet):
    serializer_class = BrokerProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "me"

    def get_object(self):
        try:
            broker = BrokerProfile.objects.get(profile__user=self.request.user)
        except BrokerProfile.DoesNotExist:
            raise NotFound("Broker profile not found.")

        if broker.status not in [BrokerProfile.Status.APPROVED, BrokerProfile.Status.SUSPENDED]:
            raise PermissionDenied("Broker is not approved.")

        return broker

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], url_path="me")
    def update_me(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

# Broker Ratings
@extend_schema_view(
    list=extend_schema(tags=["Brokers - Ratings"], description="List all ratings for a broker."),
    retrieve=extend_schema(tags=["Brokers - Ratings"], description="Retrieve a specific broker rating."),
    create=extend_schema(tags=["Brokers - Ratings"], description="Create a broker rating."),
    update=extend_schema(tags=["Brokers - Ratings"], description="Update a broker rating (owner or admin)."),
    partial_update=extend_schema(tags=["Brokers - Ratings"], description="Partially update a broker rating."),
    destroy=extend_schema(tags=["Brokers - Ratings"], description="Delete a broker rating (owner or admin)."),
)
@extend_schema(
    parameters=[
        OpenApiParameter(
            name="broker_pk",
            type=OpenApiTypes.INT,
            location="path",
            description="Broker ID",
        ),
    ]
)
class BrokerRatingViewSet(viewsets.ModelViewSet):
    serializer_class = BrokerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        broker_pk = self.kwargs.get("broker_pk")
        user = self.request.user

        if has_role(user, ['admin', 'super_admin']):
            return BrokerRating.objects.filter(broker_id=broker_pk)

        return BrokerRating.objects.filter(broker_id=broker_pk, user=user)

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsRatingOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        broker_pk = self.kwargs.get("broker_pk")
        try:
            broker = BrokerProfile.objects.get(pk=broker_pk)
        except BrokerProfile.DoesNotExist:
            raise serializers.ValidationError({"broker": "Broker does not exist."})

        serializer.save(broker=broker, user=self.request.user)
        logger.info(f"Broker rating created by {self.request.user.email} for broker {broker_pk}")


