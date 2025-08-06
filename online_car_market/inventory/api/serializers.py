from rest_framework import serializers
from rolepermissions.checkers import has_role, has_permission
from ..models import Car, CarImage
from online_car_market.dealers.models import Dealer
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime

User = get_user_model()

class CarImageSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    image = serializers.CharField()

    class Meta:
        model = CarImage
        fields = ['id', 'car', 'image', 'is_featured', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_image(self, value):
        """Validate and sanitize Cloudinary image reference."""
        if not value:
            raise serializers.ValidationError("Image is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if not re.match(r'^[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)*$', cleaned_value) and not cleaned_value.startswith('http'):
            raise serializers.ValidationError("Invalid Cloudinary image reference or URL.")
        return cleaned_value

    def validate_caption(self, value):
        """Sanitize and validate caption."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned_value
        return value

    def validate_is_featured(self, value):
        """Ensure only one image per car is featured."""
        if value and self.instance and self.instance.is_featured:
            return value
        if value:
            car = self.initial_data.get('car') or (self.instance.car.pk if self.instance else None)
            if car and CarImage.objects.filter(car_id=car, is_featured=True).exists():
                raise serializers.ValidationError("Another image is already featured for this car.")
        return value

    def validate(self, data):
        """Ensure only dealers or admins can manage images."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create car images.")
        if self.instance and data.get('car') and data['car'].posted_by != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car image.")
        return data

class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    posted_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    images = CarImageSerializer(many=True, read_only=True)
    verification_status = serializers.ChoiceField(choices=Car.VERIFICATION_STATUSES, read_only=True)

    class Meta:
        model = Car
        fields = ['id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'status', 'dealer', 'posted_by', 'verification_status', 'created_at', 'updated_at', 'images']
        read_only_fields = ['id', 'created_at', 'updated_at', 'verification_status']

    def validate_make(self, value):
        """Sanitize and validate make."""
        if not value:
            raise serializers.ValidationError("Make is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Make can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_model(self, value):
        """Sanitize and validate model."""
        if not value:
            raise serializers.ValidationError("Model is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Model can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_year(self, value):
        """Validate year."""
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year + 1}.")
        return value

    def validate_price(self, value):
        """Validate price."""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_mileage(self, value):
        """Validate mileage."""
        if value < 0:
            raise serializers.ValidationError("Mileage cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Mileage cannot exceed 1,000,000 km.")
        return value

    def validate_fuel_type(self, value):
        """Sanitize and validate fuel type."""
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_status(self, value):
        """Sanitize and validate status."""
        valid_statuses = ['available', 'reserved', 'sold', 'pending_inspection', 'under_maintenance', 'delivered', 'archived']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate_dealer(self, value):
        """Ensure dealer has dealer role and matches user."""
        if not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        user = self.context['request'].user
        if value.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can assign this dealer.")
        return value

    def validate(self, data):
        """Ensure only authorized users can create/update cars."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('posted_by') and data['posted_by'] != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")
        return data

class VerifyCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['verification_status']
        read_only_fields = []

    def validate_verification_status(self, value):
        """Ensure valid verification status."""
        valid_statuses = ['pending', 'verified', 'rejected']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Verification status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate(self, data):
        """Ensure only admins or super admins can verify cars."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data
