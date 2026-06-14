from rest_framework import serializers
from ..models import Inspection, Inspector
from online_car_market.inventory.models import Car
from online_car_market.inventory.api.serializers import CarMiniSerializer
from ..services.inspection_service import InspectionService


class InspectionSerializer(serializers.ModelSerializer):

    car = CarMiniSerializer(read_only=True)
    car_id = serializers.IntegerField(write_only=True)

    inspector_id = serializers.IntegerField(write_only=True)
    inspector = serializers.StringRelatedField(read_only=True)

    car_display = serializers.SerializerMethodField()
    report_url = serializers.SerializerMethodField()

    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True
    )

    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True
    )

    class Meta:
        model = Inspection
        fields = [
            "id",

            "car",
            "car_id",
            "car_display",

            "inspector",
            "inspector_id",

            "inspection_date",
            "remarks",
            "condition_status",

            "signed_report",
            "report_url",

            "status",

            "verified_by_email",
            "verified_at",
            "admin_remarks",

            "uploaded_by_email",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "car",
            "car_display",
            "report_url",
            "inspector",
            "verified_by_email",
            "verified_at",
            "uploaded_by_email",
            "created_at",
            "updated_at",
        ]

    def get_car_display(self, obj):
        return str(obj.car)

    def get_report_url(self, obj):
        if obj.signed_report:
            return obj.signed_report.build_url()
        return None

    def validate_car_id(self, value):
        if not Car.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Car with this ID does not exist."
            )
        return value

    def validate_inspector_id(self, value):
        if not Inspector.objects.filter(
            id=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "Inspector not found or inactive."
            )

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
