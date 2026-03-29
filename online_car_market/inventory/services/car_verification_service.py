from django.db import transaction
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

        # Lock row to prevent race conditions
        car = (
            car.__class__.objects
            .select_for_update()
            .select_related(
                "dealer__profile__user",
                "broker__profile__user"
            )
            .get(pk=car.pk)
        )

        # Idempotency protection
        if car.verification_status == verification_status:
            return car

        # Apply update
        car.verification_status = verification_status
        car.priority = verification_status == "verified"

        car.save(update_fields=["verification_status", "priority"])

        owner = None
        role = None

        if car.dealer:
            owner = car.dealer.profile.user
            role = "dealer"
        elif car.broker:
            owner = car.broker.profile.user
            role = "broker"

            # Safety check
        if not owner:
            return car

        # BUILD MESSAGE
        car_name = f"{car.make} {car.model} ({car.year})"

        if verification_status == "verified":
            if role == "dealer":
                message = f"Your dealership car '{car_name}' is now verified and live."
            else:
                message = f"Your listed car '{car_name}' has been approved."

            notif_type = "car_verified"

        elif verification_status == "rejected":
            message = f"Your car '{car_name}' was rejected. Please review and update."
            notif_type = "car_rejected"

        else:
            message = f"Your car '{car_name}' status updated to {verification_status}."
            notif_type = "car_status_update"

        # CREATE NOTIFICATION
        notify_user(
            user=owner,
            message=message,
            data={
                "car_id": car.id,
                "status": verification_status,
                "type": 'car_verification',
            }
        )

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





