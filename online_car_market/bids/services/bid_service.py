from django.db import transaction
from django.utils import timezone
from online_car_market.inventory.models import Car
from ..models import Auction, Bid

class BidService:

    @staticmethod
    @transaction.atomic
    def place_bid(user, car_id, amount):
        car = Car.objects.select_for_update().get(id=car_id)

        try:
            auction = car.auction
        except Auction.DoesNotExist:
            raise ValueError("This car has no active auction.")

        now = timezone.now()

        if auction.status != "active" or not (auction.start_at <= now <= auction.end_at):
            raise ValueError("Auction is not active.")

        highest_bid = (Bid.objects.filter(car=car).order_by("-amount").first())

        if highest_bid and amount <= highest_bid.amount:
            raise ValueError("Bid must be higher than current highest bid.")

        return Bid.objects.create(car=car, user=user, amount=amount)
