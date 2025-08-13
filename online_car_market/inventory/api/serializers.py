from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Car, CarImage
from online_car_market.dealers.models import Dealer
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime
import cloudinary.uploader
import cloudinary.utils

User = get_user_model()


# ---------------- CarImage Serializer ----------------
class CarImageSerializer(serializers.ModelSerializer):
    image_file = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_url = serializers.SerializerMethodField()  # Always returns Cloudinary URL

    class Meta:
        model = CarImage
        fields = ["id", "car", "public_id", "image_url", "is_featured", "caption", "uploaded_at", "image_file"]
        read_only_fields = ["id", "uploaded_at", "public_id", "image_url"]

    def get_image_url(self, obj):
        if obj.public_id:
            return cloudinary.utils.cloudinary_url(obj.public_id, secure=True)[0]
        return None

    def validate_caption(self, value):
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned_value
        return value

    def validate_is_featured(self, value):
        if value:
            car_obj = self.instance.car if self.instance else None
            if not car_obj and self.initial_data.get("car"):
                try:
                    car_obj = Car.objects.get(pk=self.initial_data.get("car"))
                except Car.DoesNotExist:
                    pass
            if car_obj:
                qs = CarImage.objects.filter(car=car_obj, is_featured=True)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError("Another image is already featured for this car.")
        return value

    def create(self, validated_data):
        image_file = validated_data.pop('image_file', None)
        if image_file:
            upload_result = cloudinary.uploader.upload(image_file)
            validated_data['public_id'] = upload_result['public_id']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        image_file = validated_data.pop('image_file', None)
        if image_file:
            if instance.public_id:
                cloudinary.uploader.destroy(instance.public_id)
            upload_result = cloudinary.uploader.upload(image_file)
            validated_data['public_id'] = upload_result['public_id']
        return super().update(instance, validated_data)


# ---------------- Car Serializer ----------------
class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    posted_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    images = CarImageSerializer(many=True, read_only=True)
    new_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    verification_status = serializers.ChoiceField(choices=Car.VERIFICATION_STATUSES, read_only=True)

    class Meta:
        model = Car
        fields = [
            'id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'status',
            'dealer', 'posted_by', 'verification_status', 'created_at', 'updated_at',
            'images', 'new_images'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'verification_status']

    # --- Validation methods ---
    def validate_make(self, value):
        if not value:
            raise serializers.ValidationError("Make is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Make can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_model(self, value):
        if not value:
            raise serializers.ValidationError("Model is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Model can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_year(self, value):
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year + 1}.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_mileage(self, value):
        if value < 0:
            raise serializers.ValidationError("Mileage cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Mileage cannot exceed 1,000,000 km.")
        return value

    def validate_fuel_type(self, value):
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_status(self, value):
        valid_statuses = [
            'available', 'reserved', 'sold', 'pending_inspection',
            'under_maintenance', 'delivered', 'archived'
        ]
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate_dealer(self, value):
        if not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        user = self.context['request'].user
        if value.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can assign this dealer.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('posted_by') and data['posted_by'] != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")
        return data

    # --- Create method ---
    def create(self, validated_data):
        new_images = validated_data.pop('new_images', [])
        car = Car.objects.create(**validated_data)

        for image_file in new_images:
            upload_result = cloudinary.uploader.upload(image_file)
            CarImage.objects.create(
                car=car,
                public_id=upload_result['public_id']
            )
        return car

# ---------------- Verify Car Serializer ----------------
class VerifyCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['verification_status']

    def validate_verification_status(self, value):
        valid_statuses = ['pending', 'verified', 'rejected']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Verification status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate(self, data):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data
