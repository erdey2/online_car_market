from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from ..models import Auction, Bid
from online_car_market.inventory.models import Car


class BidService:
    '''
    @staticmethod
    @transaction.atomic
    def place_bid(*, user, car_id, amount):
        try:
            auction = (
                Auction.objects
                .select_for_update()
                .get(
                    car_id=car_id,
                    status="active"
                )
            )
        except Auction.DoesNotExist:
            raise ValidationError(
                "No active auction found for this car."
            )

        now = timezone.now()

        if not (auction.start_at <= now <= auction.end_at):
            raise ValidationError(
                "Auction is not active."
            )

        highest_amount = (
            Bid.objects
            .filter(car_id=car_id)
            .aggregate(
                max=Max("amount")
            )["max"]
        )

        if (
            highest_amount is not None
            and amount <= highest_amount
        ):
            raise ValidationError(
                "Bid must be higher than current highest bid."
            )

        return Bid.objects.create(
            user=user,
            car_id=car_id,
            amount=amount
        ) '''

    @staticmethod
    @transaction.atomic
    def place_bid(*, user, car_id, amount):
        """
        Place a bid only on cars whose sale_type is 'auction'.
        """

        # Check car exists
        try:
            car = Car.objects.select_for_update().get(id=car_id)
        except Car.DoesNotExist:
            raise ValidationError(
                "Car not found."
            )

        # Ensure car is auction type
        if car.sale_type != "auction":
            raise ValidationError(
                "Bids can only be placed on auction cars."
            )

        # Get current highest bid
        highest_amount = (
            Bid.objects
            .filter(car_id=car_id)
            .aggregate(
                max=Max("amount")
            )["max"]
        )

        # Validate bid amount
        if (
            highest_amount is not None
            and amount <= highest_amount
        ):
            raise ValidationError(
                "Bid must be higher than current highest bid."
            )

        # Create bid
        return Bid.objects.create(
            user=user,
            car_id=car_id,
            amount=amount
        )

