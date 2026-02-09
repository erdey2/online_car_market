from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from ..models import Auction, Bid


class AuctionService:

    @staticmethod
    def is_active(auction: Auction) -> bool:
        now = timezone.now()
        return (
            auction.status == "open"
            and auction.start_at <= now <= auction.end_at
        )

    @staticmethod
    @transaction.atomic
    def close_auction(auction_id: int):
        auction = (
            Auction.objects
            .select_for_update()
            .get(id=auction_id)
        )

        if auction.status != "open":
            raise ValidationError("Auction is not open")

        highest_bid = (
            Bid.objects
            .filter(auction=auction)
            .order_by("-amount", "created_at")
            .first()
        )

        auction.status = "closed"
        auction.closed_at = timezone.now()
        auction.save(update_fields=["status", "closed_at"])

        return highest_bid

    @staticmethod
    @transaction.atomic
    def cancel_auction(auction_id: int):
        auction = (
            Auction.objects
            .select_for_update()
            .get(id=auction_id)
        )

        if auction.status != "open":
            raise ValidationError("Only open auctions can be cancelled")

        auction.status = "cancelled"
        auction.save(update_fields=["status"])
