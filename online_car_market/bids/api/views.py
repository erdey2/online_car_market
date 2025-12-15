from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Bid
from .serializers import BidSerializer
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from online_car_market.users.permissions.drf_permissions import IsBuyer, IsSuperAdminOrAdmin, IsDealer, IsBroker


@extend_schema_view(
    list=extend_schema(
        tags=["Bids"],
        summary="List Bids",
        description="List all bids made by the authenticated user (Buyers only).",
        responses={200: BidSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Bids"],
        summary="Create a New Bid",
        description="Create a new bid on a car. Only users with the 'buyer' role can perform this action.",
        request=BidSerializer,
        responses={201: BidSerializer},
    ),
    retrieve=extend_schema(
        tags=["Bids"],
        summary="Retrieve a Bid",
        description="Retrieve a specific bid by its ID. Only the bid owner (Buyer) can access it.",
        responses={200: BidSerializer},
    ),
    update=extend_schema(
        tags=["Bids"],
        summary="Update a Bid",
        description="Fully update a bid (e.g., change car or amount). Only the bid owner (Buyer) can perform this action.",
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    partial_update=extend_schema(
        tags=["Bids"],
        summary="Partially Update a Bid",
        description="Partially update a bid (e.g., modify amount). Only the bid owner (Buyer) can do this.",
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    destroy=extend_schema(
        tags=["Bids"],
        summary="Delete a Bid",
        description="Delete a bid. Only the bid owner (Buyer) can delete their own bid.",
        responses={204: None},
    ),
)
class BidViewSet(ModelViewSet):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = (Bid.objects.select_related("user", "user__profile", "car").order_by("-created_at"))

        if has_role(user, ["admin", "superadmin"]):
            return qs

        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "list", "retrieve"]:
            return [IsAuthenticated(), IsBuyer()]

        if self.action == "manage":
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]

        return super().get_permissions()

    # Bid history per car
    @extend_schema(
        tags=["Bids"],
        summary="Bid history per car",
        description="Retrieve all bids for a specific car, ordered by most recent.",
        responses={200: BidSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="car/(?P<car_id>[^/.]+)/history")
    def car_bid_history(self, request, car_id=None):
        bids = (
            Bid.objects
            .filter(car_id=car_id)
            .select_related("user", "user__profile", "car")
            .order_by("-created_at")
        )
        serializer = self.get_serializer(bids, many=True)
        return Response(serializer.data)

    # Admin manage bid
    @extend_schema(
        tags=["Bids"],
        summary="Approve or reject a bid",
        description="Admins or SuperAdmins can approve or reject a bid.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["approved", "rejected"]
                    }
                },
                "required": ["status"],
            }
        },
        responses={200: {"description": "Bid successfully updated"}},
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsSuperAdminOrAdmin])
    def manage(self, request, pk=None):
        bid = self.get_object()
        status_value = request.data.get("status")

        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        bid.status = status_value
        bid.save(update_fields=["status"])

        return Response(
            {"detail": f"Bid {status_value} successfully."},
            status=status.HTTP_200_OK
        )


