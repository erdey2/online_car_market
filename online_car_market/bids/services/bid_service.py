from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from ..models import Auction, Bid


class BidService:

    @staticmethod
    @transaction.atomic
    def place_bid(*, user, car_id, amount):
        auction = (
            Auction.objects
            .select_for_update()
            .get(car_id=car_id, status="open")
        )

        now = timezone.now()
        if not (auction.start_at <= now <= auction.end_at):
            raise ValidationError("Auction is not active")

        highest_amount = (
            Bid.objects
            .filter(car_id=car_id)
            .aggregate(max=Max("amount"))["max"]
        )

        if highest_amount is not None and amount <= highest_amount:
            raise ValidationError("Bid must be higher than current highest bid")

        return Bid.objects.create(
            user=user,
            car_id=car_id,
            amount=amount
        )
