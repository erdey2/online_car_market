from django.utils import timezone
from rest_framework.exceptions import ValidationError
from ..models import Inspection, Inspector
from online_car_market.inventory.models import Car
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from django.contrib.auth import get_user_model
from rolepermissions.roles import assign_role

User = get_user_model()

class InspectionService:

    @staticmethod
    def get_user_inspections(user):

        # Super Admin / Admin
        if getattr(user, "role", None) in [
            "admin",
            "super_admin"
        ]:
            return Inspection.objects.select_related(
                "car",
                "inspector",
                "verified_by"
            )

        # Inspector
        if hasattr(user, "inspector_profile"):
            return Inspection.objects.filter(
                inspector=user.inspector_profile
            )

        # Dealer
        dealer = DealerProfile.objects.filter(
            profile__user=user
        ).first()

        if dealer:
            return Inspection.objects.filter(
                car__dealer=dealer
            )

        # Broker
        broker = BrokerProfile.objects.filter(
            profile__user=user
        ).first()

        if broker:
            return Inspection.objects.filter(
                car__broker=broker
            )

        # Buyers/Public
        return Inspection.objects.filter(
            status="verified"
        )

    @staticmethod
    def verify_inspection(
        inspection,
        user,
        status_value,
        admin_remarks=""
    ):

        if status_value not in [
            "verified",
            "rejected"
        ]:
            raise ValidationError(
                "Invalid status. Must be 'verified' or 'rejected'."
            )

        inspection.status = status_value
        inspection.verified_by = user
        inspection.verified_at = timezone.now()
        inspection.admin_remarks = admin_remarks

        inspection.save()

        return inspection

    @staticmethod
    def create_inspection(
        user,
        validated_data
    ):

        if not hasattr(user, "inspector_profile"):
            raise ValidationError(
                "Only inspectors can create inspections."
            )

        car_id = validated_data.pop("car_id")

        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            raise ValidationError(
                "Car not found."
            )

        return Inspection.objects.create(
            car=car,
            inspector=user.inspector_profile,
            status="pending",
            **validated_data
        )

    @staticmethod
    def update_inspection(
        instance,
        user,
        validated_data
    ):

        # Admin verification handled separately
        validated_data.pop("status", None)

        if instance.status != "pending":
            raise ValidationError(
                "Only pending inspections can be modified."
            )

        if not hasattr(user, "inspector_profile"):
            raise ValidationError(
                "Only inspectors can modify inspections."
            )

        if instance.inspector != user.inspector_profile:
            raise ValidationError(
                "You can only modify your own inspections."
            )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance


class InspectorService:

    @staticmethod
    def create_inspector(admin_user, validated_data):

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        assign_role(user, "inspector")

        inspector = Inspector.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            license_number=validated_data.get("license_number"),
            created_by=admin_user,
        )

        return inspector
