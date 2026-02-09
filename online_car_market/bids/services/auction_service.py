from django.utils import timezone
from django.db import transaction
from ..models import Auction, Bid

class AuctionService:

    @staticmethod
    def is_active(auction: Auction) -> bool:
        now = timezone.now()
        return (
            auction.status == "active"
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

        if auction.status == "closed":
            return None  # already closed

        highest_bid = (
            Bid.objects
            .filter(car=auction.car)
            .order_by("-amount", "created_at")
            .first()
        )

        auction.status = "closed"
        auction.closed_at = timezone.now()
        auction.save(update_fields=["status", "closed_at"])

        return highest_bid
