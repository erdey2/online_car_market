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
from online_car_market.inventory.models import Car
from online_car_market.bids.api.serializers import ProfileMiniSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Bids"],
        summary="List Bids",
        description=(
            "Retrieve a list of bids.\n\n"
            "- Admins and Super Admins receive all bids.\n"
            "- Regular users receive only their own bids."
        ),
        responses={200: BidSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Bids"],
        summary="Create a New Bid",
        description=(
            "Create a new bid on a car.\n\n"
            "- The authenticated user is automatically set as the bid owner.\n"
            "- The car must be available for bidding.\n"
            "- Bid amount must be greater than zero."
        ),
        request=BidSerializer,
        responses={201: BidSerializer},
    ),
    retrieve=extend_schema(
        tags=["Bids"],
        summary="Retrieve a Bid",
        description=(
            "Retrieve a specific bid by its ID.\n\n"
            "- Admins and Super Admins can retrieve any bid.\n"
            "- Regular users can retrieve only their own bids."
        ),
        responses={200: BidSerializer},
    ),
    update=extend_schema(
        tags=["Bids"],
        summary="Update a Bid",
        description=(
            "Fully update a bid.\n\n"
            "- Admins and Super Admins can update any bid.\n"
            "- Regular users can update only their own bids."
        ),
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    partial_update=extend_schema(
        tags=["Bids"],
        summary="Partially Update a Bid",
        description=(
            "Partially update a bid (e.g., modify the bid amount).\n\n"
            "- Admins and Super Admins can update any bid.\n"
            "- Regular users can update only their own bids."
        ),
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    destroy=extend_schema(
        tags=["Bids"],
        summary="Delete a Bid",
        description=(
            "Delete a bid.\n\n"
            "- Admins and Super Admins can delete any bid.\n"
            "- Regular users can delete only their own bids."
        ),
        responses={204: None},
    ),
)
class BidViewSet(ModelViewSet):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Bid.objects.select_related("user", "user__profile", "car").order_by("-created_at")
        if has_role(user, ["admin", "superadmin"]):
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "list", "retrieve"]:
            return [IsAuthenticated(), IsBuyer()]
        if self.action == "manage":
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]
        return super().get_permissions()

    # Helper to enforce bid higher than current
    def _check_highest_bid(self, car_id, amount, current_bid_id=None):
        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            return {"error": "Car not found."}, status.HTTP_400_BAD_REQUEST

        qs = car.bids.exclude(id=current_bid_id) if current_bid_id else car.bids
        highest_bid = qs.order_by('-amount').first()
        if highest_bid and float(amount) <= float(highest_bid.amount):
            return {
                "error": "Bid must be higher than current highest bid.",
                "current_highest_bid": highest_bid.amount
            }, status.HTTP_400_BAD_REQUEST

        return None, None

    # Create
    def create(self, request, *args, **kwargs):
        car_id = request.data.get('car')
        amount = request.data.get('amount')
        error_response, status_code = self._check_highest_bid(car_id, amount)
        if error_response:
            return Response(error_response, status=status_code)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # Update / Partial Update
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        car_id = request.data.get('car', instance.car.id)
        amount = request.data.get('amount', instance.amount)
        error_response, status_code = self._check_highest_bid(car_id, amount, current_bid_id=instance.id)
        if error_response:
            return Response(error_response, status=status_code)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    # Bid history per car with top 3 and highest bid
    @extend_schema(
        tags=["Bids"],
        summary="Bid history per car",
        description="Retrieve all bids for a specific car, ordered by most recent, with current highest bid highlighted and top 3 bids shown.",
        responses={200: BidSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="car/(?P<car_id>[^/.]+)/history")
    def car_bid_history(self, request, car_id=None):
        bids = (
            Bid.objects.filter(car_id=car_id)
            .select_related("user", "user__profile", "car")
            .order_by("-created_at")
        )
        highest_bid = bids.order_by('-amount').first()
        top_bids = bids.order_by('-amount')[:3]

        serializer = self.get_serializer(bids, many=True)
        top_serializer = self.get_serializer(top_bids, many=True)

        response_data = {
            "all_bids": serializer.data,
            "highest_bid": {
                "id": highest_bid.id,
                "amount": highest_bid.amount,
                "user": highest_bid.user.id,
                "profile": ProfileMiniSerializer(highest_bid.user.profile).data,
                "created_at": highest_bid.created_at,
            } if highest_bid else None,
            "top_3_bids": top_serializer.data
        }

        return Response(response_data)

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
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        bid.status = status_value
        bid.save(update_fields=["status"])
        return Response({"detail": f"Bid {status_value} successfully."}, status=status.HTTP_200_OK)



