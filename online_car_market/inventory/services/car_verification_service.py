from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rolepermissions.checkers import has_role
from online_car_market.inventory.models import Car
from online_car_market.notifications.services import notify_user

class CarVerificationService:

    @staticmethod
    @transaction.atomic
    def verify_car(
        car,
        verification_status,
        reviewed_by=None,
    ):
        if not verification_status:
            raise ValidationError(
                "verification_status is required."
            )

        if (
            car.verification_status
            == verification_status
        ):
            return car

        car.verification_status = (
            verification_status
        )
        car.priority = (
            verification_status
            == "verified"
        )
        update_fields = [
            "verification_status",
            "priority",
        ]
        if reviewed_by:

            car.reviewed_by = reviewed_by
            car.reviewed_at = timezone.now()

            update_fields.extend(
                [
                    "reviewed_by",
                    "reviewed_at",
                ]
            )
        car.save(
            update_fields=update_fields
        )

        owner = None
        role = None

        # Dealer owner
        if car.dealer:

            owner = (
                getattr(
                    getattr(
                        car.dealer,
                        "profile",
                        None
                    ),
                    "user",
                    None
                )
            )
            role = "dealer"

        # Broker owner
        elif car.broker:

            owner = (
                getattr(
                    getattr(
                        car.broker,
                        "profile",
                        None
                    ),
                    "user",
                    None
                )
            )
            role = "broker"

        if not owner:
            return car

        car_name = (
            f"{car.make} "
            f"{car.model} "
            f"({car.year})"
        )

        if verification_status == "verified":

            if role == "dealer":

                message = (
                    f"Your dealership car "
                    f"'{car_name}' "
                    f"is now verified and live."
                )

            else:
                message = (
                    f"Your listed car "
                    f"'{car_name}' "
                    f"has been approved."
                )

        elif verification_status == "rejected":

            message = (
                f"Your car '{car_name}' "
                f"was rejected. "
                f"Please review and update."
            )

        else:
            message = (
                f"Your car '{car_name}' "
                f"status updated to "
                f"{verification_status}."
            )

        transaction.on_commit(
            lambda: notify_user(
                user=owner,
                message=message,
                data={
                    "car_id": car.id,
                    "status": verification_status,
                    "type": "car_verification",
                }
            )
        )
        return car

    @staticmethod
    def get_verification_analytics(user):

        if not has_role(
            user,
            [
                "admin",
                "super_admin",
            ]
        ):

            raise PermissionDenied(
                "You are not allowed to access verification analytics."
            )

        aggregated = (
            Car.objects
            .values(
                "verification_status"
            )
            .annotate(
                count=Count("id")
            )
        )

        stats = {
            "total": 0,
            "pending": 0,
            "verified": 0,
            "rejected": 0,
        }

        for item in aggregated:

            status = (
                item["verification_status"]
            )

            count = item["count"]


            stats["total"] += count


            if status in stats:

                stats[status] = count

        return stats
