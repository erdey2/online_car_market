from rest_framework.exceptions import ValidationError

class CarBidService:

    @staticmethod
    def place_bid(car, serializer):
        if car.sale_type != "auction":
            raise ValidationError("Bids can only be placed on auction cars.")

        return serializer.save(car=car)
