from rest_framework import serializers
from ..models import Inspection
from online_car_market.inventory.models import Car
from ..services.inspection_service import InspectionService

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
        return InspectionService.create_inspection(
            user=self.context["request"].user,
            validated_data=validated_data
        )

    def update(self, instance, validated_data):
        return InspectionService.update_inspection(
            instance=instance,
            user=self.context["request"].user,
            validated_data=validated_data
        )
