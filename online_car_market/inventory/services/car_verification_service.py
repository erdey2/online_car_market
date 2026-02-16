from django.db import transaction
from rest_framework.exceptions import ValidationError


class CarVerificationService:

    @staticmethod
    @transaction.atomic
    def verify_car(car, verification_status):
        if verification_status is None:
            raise ValidationError("verification_status is required.")

        # Lock row to prevent race conditions
        car = (
            car.__class__.objects
            .select_for_update()
            .get(pk=car.pk)
        )

        # Idempotency protection
        if car.verification_status == verification_status:
            return car

        # Apply business rule
        car.verification_status = verification_status
        car.priority = verification_status == "verified"

        car.save(update_fields=["verification_status", "priority"])

        return car



