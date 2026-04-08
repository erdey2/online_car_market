from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from online_car_market.inventory.models import Car
from rolepermissions.checkers import has_role
from django.db.models import Count
from online_car_market.notifications.services import notify_user


class CarVerificationService:

    @staticmethod
    @transaction.atomic
    def verify_car(car, verification_status, reviewed_by=None):

        if verification_status is None:
            raise ValidationError("verification_status is required.")

        if car.verification_status == verification_status:
            return car

        car.verification_status = verification_status
        car.priority = verification_status == "verified"

        if reviewed_by:
            car.reviewed_by = reviewed_by
            car.reviewed_at = timezone.now()

        car.save(update_fields=[
            "verification_status",
            "priority",
            "reviewed_by",
            "reviewed_at"
        ])

        owner = None
        role = None

        if car.dealer:
            owner = car.dealer.profile.user
            role = "dealer"
        elif car.broker:
            owner = car.broker.profile.user
            role = "broker"

        if not owner:
            return car

        car_name = f"{car.make} {car.model} ({car.year})"

        if verification_status == "verified":
            message = (
                f"Your dealership car '{car_name}' is now verified and live."
                if role == "dealer"
                else f"Your listed car '{car_name}' has been approved."
            )
        elif verification_status == "rejected":
            message = f"Your car '{car_name}' was rejected. Please review and update."
        else:
            message = f"Your car '{car_name}' status updated to {verification_status}."

        transaction.on_commit(lambda: notify_user(
            user=owner,
            message=message,
            data={
                "car_id": car.id,
                "status": verification_status,
                "type": "car_verification",
            }
        ))

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





