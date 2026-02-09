from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Bid, Auction
from .serializers import BidSerializer, AuctionSerializer
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from online_car_market.users.permissions.drf_permissions import IsBuyer, IsSuperAdminOrAdmin
from online_car_market.bids.services import bid_service, auction_service


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
)
class BidViewSet(ModelViewSet):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        user = self.request.user
        qs = (
            Bid.objects
            .select_related("user", "user__profile", "car")
            .order_by("-created_at")
        )

        if has_role(user, ["admin", "superadmin"]):
            return qs

        return qs.filter(user=user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsBuyer()]

        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]

        if self.action == "manage":
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]

        return super().get_permissions()

    # CREATE (SAFE)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bid = bid_service.place_bid(
            user=request.user,
            car_id=serializer.validated_data["car"].id,
            amount=serializer.validated_data["amount"]
        )

        return Response(
            BidSerializer(bid, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )

    # BID HISTORY (READ ONLY)
    @extend_schema(
        tags=["Bids"],
        summary="Bid history per car",
        description="Returns all bids, the highest bid, and top 3 bids for a car."
    )
    @action(detail=False, methods=["get"], url_path="car/(?P<car_id>[^/.]+)/history")
    def car_bid_history(self, request, car_id=None):
        bids = (
            Bid.objects
            .filter(car_id=car_id)
            .select_related("user", "user__profile", "car")
            .order_by("-created_at")
        )

        ranked = bids.order_by("-amount")
        highest_bid = ranked.first()
        top_bids = ranked[:3]

        return Response({
            "all_bids": BidSerializer(bids, many=True).data,
            "highest_bid": BidSerializer(highest_bid).data if highest_bid else None,
            "top_3_bids": BidSerializer(top_bids, many=True).data,
        })

@extend_schema_view(
    list=extend_schema(
        tags=["Auctions"],
        summary="List Auctions",
        description="Admins can list all auctions."
    ),
    retrieve=extend_schema(
        tags=["Auctions"],
        summary="Retrieve an Auction",
        description="Get auction details."
    )
)
class AuctionViewSet(ModelViewSet):
    serializer_class = AuctionSerializer
    queryset = Auction.objects.all()
    permission_classes = [IsAuthenticated, IsSuperAdminOrAdmin]
    http_method_names = ['get', 'post', 'patch']

    @extend_schema(
        tags=["Auctions"],
        summary="Close Auction",
        description="Super admin closes the auction and determines the winner."
    )
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        auction = self.get_object()
        highest_bid = auction_service.close_auction(auction.id)

        return Response({
            "status": "closed",
            "winner": highest_bid.user.id if highest_bid else None,
            "amount": highest_bid.amount if highest_bid else None
        })

    @extend_schema(
        tags=["Auctions"],
        summary="Cancel Auction",
        description="Super admin cancels an auction (optional)."
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        auction = self.get_object()
        auction.status = "cancelled"
        auction.save(update_fields=["status"])
        return Response({"detail": "Auction cancelled"}, status=status.HTTP_200_OK)







