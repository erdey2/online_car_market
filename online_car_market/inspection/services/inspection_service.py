from rest_framework.exceptions import ValidationError
from django.utils import timezone
from rolepermissions.checkers import has_role
from ..models import Inspection
from online_car_market.inventory.models import Car

class InspectionService:

    @staticmethod
    def get_user_inspections(user):
        if has_role(user, ["admin", "superadmin"]):
            return Inspection.objects.all()
        return Inspection.objects.filter(uploaded_by=user)

    @staticmethod
    def verify_inspection(inspection, user, status_value, admin_remarks):
        if status_value not in ["verified", "rejected"]:
            raise ValidationError("Invalid status. Must be 'verified' or 'rejected'.")

        inspection.status = status_value
        inspection.verified_by = user
        inspection.verified_at = timezone.now()
        inspection.admin_remarks = admin_remarks
        inspection.save()

        return inspection

    @staticmethod
    def create_inspection(user, validated_data):
        car = Car.objects.get(id=validated_data.pop("car_id"))

        return Inspection.objects.create(
            car=car,
            uploaded_by=user,
            uploaded_at=timezone.now(),
            status="pending",
            **validated_data
        )

    @staticmethod
    def update_inspection(instance, user, validated_data):
        if "status" in validated_data and validated_data["status"] in ["verified", "rejected"]:
            if not (user.is_staff or user.role in ["admin", "superadmin"]):
                raise ValidationError("Only admin or superadmin can verify inspections.")

            instance.status = validated_data["status"]
            instance.verified_by = user
            instance.verified_at = timezone.now()
            instance.admin_remarks = validated_data.get("admin_remarks", instance.admin_remarks)

        else:
            if instance.status != "pending":
                raise ValidationError("Only pending inspections can be modified.")

            if instance.uploaded_by != user:
                raise ValidationError("You can only modify your own inspection.")

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

        instance.save()
        return instance
