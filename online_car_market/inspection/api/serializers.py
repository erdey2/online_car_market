from rest_framework import serializers
from ..models import Inspection, Inspector
from online_car_market.inventory.models import Car
from online_car_market.inventory.api.serializers import CarMiniSerializer
from ..services.inspection_service import InspectionService


class InspectionSerializer(serializers.ModelSerializer):

    car = CarMiniSerializer(read_only=True)
    car_id = serializers.IntegerField(write_only=True)

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

class InspectorSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = Inspector
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "company_name",
            "license_number",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "email",
        ]

    def get_first_name(self, obj):
        if hasattr(obj.user, "profile"):
            return obj.user.profile.first_name
        return ""

    def get_last_name(self, obj):
        if hasattr(obj.user, "profile"):
            return obj.user.profile.last_name
        return ""

class CreateInspectorSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    company_name = serializers.CharField()
    license_number = serializers.CharField(required=False)

    password = serializers.CharField(write_only=True)

class InspectionVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["verified", "rejected"]
    )

    admin_remarks = serializers.CharField(
        required=False,
        allow_blank=True
    )
