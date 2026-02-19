from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from online_car_market.inventory.models import Car
from rolepermissions.checkers import has_role
from django.db.models import Count, Q


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

    @staticmethod
    def get_verification_analytics(user):
        qs = Car.objects.all()

        # Only admin/super admin should access global analytics
        if not has_role(user, ["admin", "super_admin"]):
            raise PermissionDenied(
                "You are not allowed to access verification analytics."
            )

        total = qs.count()

        aggregated = qs.values("verification_status").annotate(
            count=Count("id")
        )

        stats = {
            "total": total,
            "pending": 0,
            "verified": 0,
            "rejected": 0,
        }

        for item in aggregated:
            stats[item["verification_status"]] = item["count"]

        return stats





