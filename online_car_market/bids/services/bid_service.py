from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from online_car_market.bids.models import Bid
from online_car_market.inventory.models import Car


class BidService:
    @staticmethod
    def place_bid(*, user, car_id, amount):
        """
        Place a bid safely with full race-condition protection.
        """

        with transaction.atomic():
            # 🔒 Lock the car row (this serializes bids per car)
            car = (
                Car.objects
                .select_for_update()
                .get(id=car_id)
            )

            # Get current highest bid (locked by transaction)
            highest_bid = (
                Bid.objects
                .filter(car=car)
                .aggregate(max_amount=Max("amount"))
                ["max_amount"]
            ) or 0

            if amount <= highest_bid:
                raise ValidationError(
                    f"Bid must be higher than current highest bid ({highest_bid})"
                )

            bid = Bid.objects.create(
                car=car,
                user=user,
                amount=amount
            )

            return bid
