from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

from ..models import Bid, Auction
from .serializers import BidSerializer, AuctionSerializer
from online_car_market.users.permissions.drf_permissions import (IsBuyer, IsSuperAdminOrAdmin)
from online_car_market.users.models import User
from online_car_market.bids.services.bid_service import BidService
from online_car_market.bids.services.auction_service import AuctionService


@extend_schema_view(
    list=extend_schema(
        tags=["Bids"],
        summary="List Bids",
        description="Admins see all bids. Users see only their own."
    ),
    create=extend_schema(
        tags=["Bids"],
        summary="Place Bid",
        description="Place a new bid on an active auction."
    ),
    retrieve=extend_schema(
        tags=["Bids"],
        summary="Retrieve Bid"
    ),
)
class BidViewSet(ModelViewSet):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        user = self.request.user

        qs = Bid.objects.select_related(
            "user",
            "user__profile",
            "car"
        )

        # Admins can see all bids
        if user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
            return qs.order_by("-created_at")

        # Buyers see only their own bids
        return qs.filter(user=user).order_by("-created_at")

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsBuyer()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bid = BidService.place_bid(
            user=request.user,
            car_id=serializer.validated_data["car"].id,
            amount=serializer.validated_data["amount"],
        )

        return Response(
            self.get_serializer(bid).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=["Bids"],
        summary="Bid history per car"
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="car/(?P<car_id>[^/.]+)/history"
    )
    def car_bid_history(self, request, car_id=None):
        bids = (
            Bid.objects
            .filter(car_id=car_id)
            .select_related(
                "user",
                "user__profile",
                "car"
            )
            .order_by("-created_at")
        )

        ranked = bids.order_by("-amount")

        return Response({
            "all_bids": BidSerializer(
                bids,
                many=True
            ).data,
            "highest_bid": BidSerializer(
                ranked.first()
            ).data if ranked.exists() else None,
            "top_3_bids": BidSerializer(
                ranked[:3],
                many=True
            ).data,
        })

@extend_schema_view(
    list=extend_schema(
        tags=["Auctions"],
        summary="List Auctions",
        description="Admins can list all auctions."
    ),
    create=extend_schema(
        tags=["Auctions"],
        summary="Create Auction",
        description="Create a new auction for a car. Admins only."
    ),
    retrieve=extend_schema(tags=["Auctions"]),
)
class AuctionViewSet(ModelViewSet):
    serializer_class = AuctionSerializer
    queryset = Auction.objects.all()
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_permissions(self):
        if self.action in ["list", "create", "retrieve", "close", "cancel"]:
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]
        return super().get_permissions()

    @extend_schema(
        tags=["Auctions"],
        summary="Close Auction"
    )
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        highest_bid = AuctionService.close_auction(pk)

        return Response({
            "status": "closed",
            "winner": highest_bid.user.id if highest_bid else None,
            "amount": highest_bid.amount if highest_bid else None,
        })

    @extend_schema(
        tags=["Auctions"],
        summary="Cancel Auction"
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        AuctionService.cancel_auction(pk)

        return Response(
            {"detail": "Auction cancelled"},
            status=status.HTTP_200_OK
        )
