from online_car_market.brokers.services import approve_broker, reject_broker, suspend_broker, reactivate_broker
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, mixins, viewsets, serializers
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
        tags=["Brokers - Applications"],
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
            rejected.telebirr_account = request.data.get(
                "telebirr_account", rejected.telebirr_account
            )
            # Reset review metadata for audit clarity
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

# Admin Broker Actions
@extend_schema(
    tags=["Admin - Broker Management"],
    parameters=[
        OpenApiParameter(
            name="id",
            type=OpenApiTypes.INT,
            location="path",
            description="User ID of the broker"
        ),
        OpenApiParameter(
            name="action",
            type=OpenApiTypes.STR,
            location="path",
            enum=["approve", "reject", "suspend", "reactivate"],
            description="Action to perform on the broker"
        ),
        OpenApiParameter(
            name="rejection_reason",
            type=OpenApiTypes.STR,
            location="body",
            required=False,
            description="Reason for rejecting a broker (required if action is reject)"
        )
    ],
    description="Perform an admin action on a broker by User ID. Actions: approve, reject, suspend, reactivate."
)
class AdminBrokerActionView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    def post(self, request, id, action):
        """
        Perform admin action on broker identified by User ID.
        """
        # Lookup BrokerProfile by User ID
        try:
            broker = BrokerProfile.objects.get(profile__user__id=id)
        except BrokerProfile.DoesNotExist:
            return Response(
                {"detail": "Broker not found for this user"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Map actions to service functions
        actions_map = {
            "approve": approve_broker,
            "reject": reject_broker,
            "suspend": suspend_broker,
            "reactivate": reactivate_broker,
        }

        service = actions_map.get(action)
        if not service:
            return Response(
                {"detail": f"Invalid action '{action}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if action == "reject":
                reason = request.data.get("rejection_reason")
                if not reason:
                    return Response(
                        {"detail": "rejection_reason is required for rejection"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                service(broker, request.user, reason)
            else:
                service(broker, request.user)

        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Admin {request.user.email} performed {action} on broker {broker.pk}")
        return Response(
            {"detail": f"Broker successfully {action}ed."},
            status=status.HTTP_200_OK
        )


# Broker Profile ViewSet
@extend_schema_view(
    me=extend_schema(
        tags=["Brokers - Profile"],
        summary="Get my broker profile",
        description="Returns the authenticated broker's own profile.",
    ),
    update_me=extend_schema(
        tags=["Brokers - Profile"],
        summary="Update my broker profile",
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

# Broker Verification
@extend_schema_view(
    verify=extend_schema(
        tags=["Brokers - Verification"],
        request=VerifyBrokerSerializer,
        responses={
            200: VerifyBrokerSerializer,
            404: OpenApiResponse(description="Broker not found."),
            403: OpenApiResponse(description="Permission denied."),
        },
        description="Verify a broker profile (admin/super_admin only).",
    )
)
class BrokerVerificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsAdmin]

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        try:
            broker = BrokerProfile.objects.get(pk=pk)
        except BrokerProfile.DoesNotExist:
            return Response({"error": "Broker not found."}, status=status.HTTP_404_NOT_FOUND)

        if broker.status != BrokerProfile.Status.APPROVED:
            return Response({"error": "Only approved brokers can be verified."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VerifyBrokerSerializer(broker, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f"Broker {broker.pk} verification updated by {request.user.email}")
        return Response(serializer.data)
