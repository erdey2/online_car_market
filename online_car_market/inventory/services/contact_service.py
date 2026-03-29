from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from django.shortcuts import get_object_or_404
from ..models import Car, DealerProfile, BrokerProfile
from online_car_market.notifications.services import notify_user

class ContactService:

    @staticmethod
    def check_admin(user):
        if not (user.is_staff or getattr(user, "is_super_admin", False)):
            raise PermissionDenied("Only admins can perform this action.")

    @staticmethod
    def get_profile(car_id=None, dealer_id=None, broker_id=None):

        if car_id:
            car = get_object_or_404(Car, id=car_id)
            user = car.posted_by

            profile = getattr(user, "profile", None)

            if profile is None:
                raise ValidationError(
                    f"User {user.id} has no profile. Please complete profile setup."
                )

            return profile


    @staticmethod
    def notify_contact_created(sender, recipient_profile, contact):
        recipient_user = recipient_profile.user

        if sender == recipient_user:
            return

        car = contact.car

        if car:
            message = (
                f"{sender.email} is interested in your "
                f"{car.make} {car.model} ({car.year})"
            )
        else:
            message = f"New contact request from {sender.email}"

        notify_user(
            user=recipient_user,
            message=message,
            data={
                "type": "contact_request",
                "sender_id": sender.id,
                "contact_id": contact.id,
                "car_id": car.id if car else None,
                "phone": contact.phone,
                "message": contact.message,
            }
        )
