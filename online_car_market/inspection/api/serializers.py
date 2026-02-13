from rest_framework import serializers
from ..models import Inspection
from django.utils import timezone
from online_car_market.inventory.models import Car

class InspectionSerializer(serializers.ModelSerializer):
    car_id = serializers.IntegerField(write_only=True, required=True)
    car_display = serializers.CharField(source='car.title', read_only=True)
    report_url = serializers.SerializerMethodField(read_only=True)
    verified_by_email = serializers.EmailField(source="verified_by.email", read_only=True)

    class Meta:
        model = Inspection
        fields = [
            "id",
            "car_id", "car_display",
            "inspected_by",
            "inspection_date",
            "remarks",
            "condition_status",
            "report_document", "report_url",
            "status",
            "verified_by_email", "verified_at", "admin_remarks",
            "uploaded_by", "uploaded_at",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "car_display", "report_url",
            "uploaded_by", "uploaded_at",
            "verified_by_email", "verified_at",
            "created_at", "updated_at"
        ]

    def get_report_url(self, obj):
        return obj.report_document.build_url() if obj.report_document else None

    def validate_car_id(self, value):
        try:
            car = Car.objects.get(id=value)
        except Car.DoesNotExist:
            raise serializers.ValidationError("Car with this ID does not exist.")
        if hasattr(car, "inspection"):
            raise serializers.ValidationError("This car already has an inspection record.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        car = Car.objects.get(id=validated_data.pop("car_id"))

        # Dealer/Broker create — always pending
        inspection = Inspection.objects.create(
            car=car,
            uploaded_by=request.user,
            uploaded_at=timezone.now(),
            status="pending",
            **validated_data
        )
        return inspection

    def update(self, instance, validated_data):
        request = self.context["request"]
        user = request.user

        # Admin verifies or rejects
        if "status" in validated_data and validated_data["status"] in ["verified", "rejected"]:
            if not (user.is_staff or user.role in ["admin", "superadmin"]):
                raise serializers.ValidationError("Only admin or superadmin can verify inspections.")
            instance.status = validated_data["status"]
            instance.verified_by = user
            instance.verified_at = timezone.now()
            instance.admin_remarks = validated_data.get("admin_remarks", instance.admin_remarks)
        else:
            # Dealers/Brokers can only edit their own pending inspections
            if instance.status != "pending":
                raise serializers.ValidationError("Only pending inspections can be modified.")
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

        instance.save()
        return instance
