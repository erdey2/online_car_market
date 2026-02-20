from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from django.shortcuts import get_object_or_404
from ..models import Car, DealerProfile, BrokerProfile

class ContactService:
    @staticmethod
    def check_admin(user):
        if not (user.is_staff or getattr(user, "is_super_admin", False)):
            raise PermissionDenied("Only admins can list all contacts.")

    @staticmethod
    def get_profile(car_id=None, dealer_id=None, broker_id=None):
        # Validate input
        if not any([car_id, dealer_id, broker_id]):
            raise ValidationError("Please provide car_id, dealer_id, or broker_id.")

        if sum(bool(x) for x in [car_id, dealer_id, broker_id]) > 1:
            raise ValidationError("Please provide only one of car_id, dealer_id, or broker_id.")

        # Retrieve profile
        if car_id:
            car = get_object_or_404(Car, id=car_id)
            return car.posted_by.profile
        elif dealer_id:
            dealer = get_object_or_404(DealerProfile, id=dealer_id)
            return dealer.profile
        elif broker_id:
            broker = get_object_or_404(BrokerProfile, id=broker_id)
            return broker.profile
        else:
            raise ValidationError("Invalid request.")
